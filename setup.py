import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="continuousEngine",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    scripts=['bin/continuous-battlecode', 'bin/continuous-client', 'bin/continuous-server', 'bin/continuous-game']
)