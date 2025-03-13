from setuptools import setup, find_packages

setup(
    name="crypto",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "cryptography",
        "tqdm",
        "psutil",
        "rarfile",
        "pywin32",
        "wmi",
        "par2deep",
    ],
    entry_points={
        "console_scripts": [
            "crypto=crypto.__main__:main",
        ],
    },
) 