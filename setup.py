from setuptools import setup, find_packages, Command
import sys
import os
from shutil import rmtree

# Package meta-data.
NAME = "mqtt-sn-gateway"
DESCRIPTION = "An async Python MQTT-SN Gayeway"
URL = "https://github.com/u9n/mqtt-sn-gateway"
EMAIL = "henrik@pwit.se"
AUTHOR = "Henrik Palmlund Wahlgren @ Palmlund Wahlgren Innovative Technology AB"
REQUIRES_PYTHON = ">=3.7"
VERSION = "21.0.0"

# What packages are required for this module to be executed?
REQUIRED = [
    "attrs==21.2.0",
    "click==8.0.1",
    "asyncio-mqtt==0.9.1",
    "asyncio-dgram==2.0.0",
    "uvloop==0.15.2",
    "structlog==21.1.0",
]

# What packages are optional?
EXTRAS = {
    # 'fancy feature': ['django'],
}

here = os.path.abspath(os.path.dirname(__file__))


class UploadCommand(Command):
    """Support setup.py upload."""

    description = "Build and publish the package."
    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print("\033[1m{0}\033[0m".format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status("Removing previous builds…")
            rmtree(os.path.join(here, "dist"))
        except OSError:
            pass

        self.status("Building Source and Wheel (universal) distribution…")
        os.system("{0} setup.py sdist bdist_wheel".format(sys.executable))

        self.status("Uploading the package to PyPI via Twine…")
        os.system("twine upload dist/*")

        self.status("Pushing git tags…")
        # os.system('git tag v{0}'.format(about['__version__']))
        os.system("git push --tags")

        sys.exit()


with open("README.md") as readme_file:
    readme = readme_file.read()

with open("HISTORY.md") as history_file:
    history = history_file.read()


setup(
    name=NAME,
    version=VERSION,
    python_requires=REQUIRES_PYTHON,
    description=DESCRIPTION,
    long_description=readme + "\n\n" + history,
    long_description_content_type="text/markdown",
    author=AUTHOR,
    author_email=EMAIL,
    url=URL,
    packages=find_packages(exclude=("tests",)),
    entry_points={"console_scripts": ["mqtt-sn-gateway=mqtt_sn_gateway.main:main"]},
    install_requires=REQUIRED,
    extras_require=EXTRAS,
    include_package_data=True,
    license="MIT",
    zip_safe=False,
    keywords=[],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Software Development :: Libraries",
    ],
    # $ setup.py publish support.
    cmdclass={"upload": UploadCommand},
)
