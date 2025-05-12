from setuptools import setup, find_packages


with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="pocketoptionapi",
    version="0.1.1",
    author="Mdbaizidtanvir",
    description="API for integration with PocketOption",
    long_description_content_type="text/markdown",
    url="https://github.com/Mdbaizidtanvir/pocketoptionapi.git",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=requirements,
) 
