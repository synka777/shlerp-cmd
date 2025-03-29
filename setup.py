from setuptools import setup, find_packages
import platform

# Perform OS check before installation
if platform.system() not in ['Darwin', 'Linux']:
    raise RuntimeError("This package only supports macOS and Linux/Unix systems.")

setup(
    name="shlerp-cmd",
    version="1.5",
    packages=find_packages(),
    install_requires=[
        "click==8.1.7",
        "requests==2.32.3",
        "pytz==2024.2",
    ],
    scripts=["shlerp/config/shlerp"],
    author="Mathieu Barbe-Gayet",
    author_email="m.barbegayet@gmail.com",
    description="Swift & Smart Backups for Any Code Flavor! ",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/synka777/shlerp-cmd",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later",
        "Operating System :: MacOS X",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.6",
    include_package_data=True
)
