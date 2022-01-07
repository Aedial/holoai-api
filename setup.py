import setuptools

with open("README.md") as f:
    long_description = f.read()

setuptools.setup(
    name = "holoai-api",
    version = "0.1",
    author = "Arthus Leroy",
    author_email = "arthus.leroy@epita.fr",
    url = "https://github.com/arthus-leroy/holoai-api/",
    description= "Python API for the HoloAI REST API",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    packages = setuptools.find_packages(),
    include_package_data = True,
    license = "MIT license",
    classifiers = [
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir = { "holoai-api": "holoai_api" },
    python_requires = '>=3.7',
    keywords = [ "python", "HoloAI", "API" ],
    install_requires = [
		"aiohttp",
        "jsonschema",
        "requests"
	]
)
