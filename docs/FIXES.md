# Car Showroom App — Fix Log

This document records three bugs found in the `car_showroom` app source,
their root causes, and the fixes applied. All three are now corrected in
this package (`car_showroom_v4_fixed.zip` and later).

---

## 1. Workspace tile missing from the Desk home page

**Symptom:** The "Car Showroom" workspace never appeared as a tile on the
Desk home page (`/desk`), even though the `Workspace` record existed,
was `public`, not hidden, had a valid icon, and had no role restrictions.

**Root cause:** The workspace fixture

```
car_showroom/car_showroom/workspace/car_showroom/car_showroom.json
```

was missing the top-level `"type"` field. Frappe 16's workspace list
builder (`frappe.desk.desktop.get_workspaces`) reads `type` as a plain
DB column via `frappe.get_all(..., fields=["type", ...])`, and every
correctly-synced workspace has `"type": "Workspace"`. With `type` unset
(`null`), the record silently failed to group into the sidebar/desk
tile list — no error was raised anywhere in the pipeline.

A second, related effect: Frappe 16 also derives the Desk **sidebar**
navigation (`frappe.boot.workspace_sidebar_item`, built from a separate
`Workspace Sidebar` / `Workspace Sidebar Item` doctype pair) from the
workspace. A `Workspace Sidebar` record has to exist for the workspace
to appear in the left-hand nav tree at all; it is not auto-created from
the `Workspace` doctype, so a first-time app install needs a fixture
for it as well as for `Workspace` itself.

**Fix:**
- Added `"type": "Workspace"` to `car_showroom.json`.
- (Applied live-only, not shippable as a fixture in this pass: created
  the corresponding `Workspace Sidebar` record for "Car Showroom" with
  a `Home` row (`link_type: Workspace`, `link_to: Car Showroom`)
  followed by one row per shortcut, `link_type` set to `DocType` or
  `Report` to match each shortcut's actual target type.)

---

## 2. `AttributeError: 'NotificationSettings' object has no attribute 'enabled'`

**Symptom:** Saving *any* `User` document (e.g. adding a role to
Administrator) crashed with:

```
AttributeError: 'NotificationSettings' object has no attribute 'enabled'
```

thrown from Frappe core's
`frappe/desk/doctype/notification_settings/notification_settings.py`,
inside `toggle_notifications()`.

**Root cause:** This app shipped its own **Single** doctype named
exactly `"Notification Settings"`
(`car_showroom/doctype/notification_settings/`), with its own
controller class also named `NotificationSettings`. Frappe DocType
names are unique per site — `tabDocType.name` is the primary key —
so this collided directly with **Frappe's built-in core doctype of
the same name**, which stores each user's notification-bell
preferences and expects a field called `enabled`. Syncing this app's
version of "Notification Settings" overwrote the core doctype's field
list with the app's own custom SMS/WhatsApp/email fields, which is
what broke `toggle_notifications()` on every subsequent User save.

**Fix:** Renamed the app's doctype to avoid any collision with
reserved core/ERPNext names:

| | Before | After |
|---|---|---|
| DocType name | `Notification Settings` | `Car Showroom Notification Settings` |
| Folder | `doctype/notification_settings/` | `doctype/car_showroom_notification_settings/` |
| Controller class | `NotificationSettings` | `CarShowroomNotificationSettings` |

Updated every reference:
- `car_showroom/reminders.py` — all three `frappe.get_single("Notification Settings")` calls
- `workspace/car_showroom/car_showroom.json` — the Settings card's `link_to` value (display `label` left as "Notification Settings" for the UI)

**Deploying this fix on an already-affected site** also requires
restoring Frappe's own core doctype metadata, since it was corrupted
by the collision:

```bash
bench --site <site> console
```
```python
frappe.reload_doc("desk", "doctype", "notification_settings", force=True)
frappe.db.commit()
```
```bash
bench --site <site> migrate
bench build
bench restart
```

---

## 3. `Vehicle Trade In` doctype repeatedly vanishing after every `bench migrate`

**Symptom:** The `Vehicle Trade In` doctype would periodically
disappear from the database entirely (`frappe.db.exists("DocType",
"Vehicle Trade In")` → `None`), breaking:
- Saving any `Vehicle Sale` with a trade-in linked (`LinkValidationError: Could not find Row #17: Link To: Vehicle Trade In`)
- The Car Showroom workspace's "Modules" section (see below)

Manually restoring it with `frappe.reload_doc(..., force=True)` always
worked — but it would vanish again on the next `bench migrate`.

**Root cause:** Frappe's migrate process includes an orphan-doctype
cleanup step (`frappe.model.sync.remove_orphan_doctypes()`) that calls
`get_controller(doctype)` for every DocType record. `get_controller`
imports the doctype's Python controller module and looks for a class
whose name exactly matches the doctype name with spaces and hyphens
stripped — for `Vehicle Trade In`, it expects a class named
**`VehicleTradeIn`**.

The controller file shipped with the app instead defined:

```python
class TradeIn(Document):
    ...
```

`getattr(module, "VehicleTradeIn", None)` returned `None`, so
`get_controller()` raised `ImportError`. Migrate's cleanup step
treats any doctype whose controller fails to import as **orphaned**
and deletes it outright — silently, with only a one-line "Orphaned
DocType(s) found: Vehicle Trade In" notice in the migrate output.
This repeated on every migrate because the underlying class name in
the source file was never corrected, only the DB record was
re-synced from that same (buggy) source each time.

A full scan of every other doctype in the app for this same
class-name pattern found no other instances — this was isolated to
`Vehicle Trade In`.

**Fix:** Renamed the controller class:

```python
# doctype/vehicle_trade_in/vehicle_trade_in.py
class VehicleTradeIn(Document):   # was: class TradeIn(Document):
    def validate(self):
        self.calculate_net_value()

    def calculate_net_value(self):
        self.net_trade_in_value = flt(self.trade_in_value) - flt(self.outstanding_finance)
```

**Deploying this fix on an already-affected site:**

```bash
rm -rf ~/frappe-bench/apps/car_showroom/car_showroom/car_showroom/doctype/vehicle_trade_in/__pycache__
```
```bash
bench --site <site> console
```
```python
frappe.reload_doc("car_showroom", "doctype", "vehicle_trade_in", force=True)
frappe.db.commit()
from frappe.model.base_document import get_controller
print(get_controller(doctype="Vehicle Trade In"))   # should now succeed
```
```bash
bench --site <site> migrate 2>&1 | grep -i orphan   # should print nothing
```

---

## 4. Vehicle's "Documents" grid showed no columns — attach field unreachable

**Symptom:** On the Vehicle form, the "Documents" child table grid
rendered with no visible columns at all (just a row-select checkbox
and a settings gear), even though rows could be added. There was no
apparent way to attach a file from the grid.

**Root cause:** The child doctype `Vehicle Document` already had a
proper `Attach`-type field (`attachment`), alongside `document_type`,
`expiry_date`, and `notes` — but **none of its fields had
`in_list_view` set**. Frappe's compact grid view only shows columns
for fields explicitly flagged `in_list_view: 1`; with none set, the
grid has nothing to display.

**Fix:** Set `"in_list_view": 1` on `document_type`, `attachment`,
and `expiry_date` in
`doctype/vehicle_document/vehicle_document.json`, so the grid shows
those three columns directly (attach button included) without needing
to open each row individually. `notes` was left off the compact view
(still editable from the row detail).

---

## General diagnostic notes for future issues in this app

- **A workspace tile silently missing?** Check `Workspace.type` first,
  then confirm a matching `Workspace Sidebar` record exists
  (`frappe.db.exists("Workspace Sidebar", "<name>")`).
- **A workspace's "Modules" cards silently empty?** The card-building
  function (`Workspace.get_links()` in `frappe/desk/desktop.py`) is
  wrapped in a decorator that catches `DoesNotExistError` and returns
  an **empty list for the whole function**, not just the one bad
  item. One broken link (missing doctype, failed controller import)
  is enough to wipe every card. Reproduce the loop manually,
  per-item, with your own try/except to find which link is at fault.
- **A doctype vanishing after migrate, with an "Orphaned DocType(s)
  found" message?** This always means `get_controller()` failed for
  that doctype — almost always a controller class name that doesn't
  exactly match `doctype_name.replace(" ", "").replace("-", "")`, or
  a Python import error inside the controller file. Check that first,
  before assuming a schema/DB issue.
- **Never name a custom doctype the same as a Frappe core or ERPNext
  doctype.** DocType names are global per site; a collision silently
  corrupts the existing doctype's schema rather than raising a clear
  "already exists" error at sync time.
