import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="crobat", 
    version="0.0.1",
    author="Ivan E. Perez",
    author_email="perez.ivan.e@gmail.com",
    description="Cryptocurrency Order Book Analysis Tool",
    long_description = long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/IEPEREZ/crobat",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU GPLv3",
        "Operating System :: OS Independent"
    ],
    python_requires='>=3.6'
)
