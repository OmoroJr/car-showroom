from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

setup(
	name="car_showroom",
	version="0.0.1",
	description="Enterprise Car Dealership, Showroom, Vehicle Sales & Hire Purchase Management ERP",
	author="Mombasa Auto Group",
	author_email="admin@example.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires,
)
