# setup.py
from setuptools import setup, Extension

module = Extension(
    "cSigner",
    sources=["sign_ext.c"],
    libraries=["dl"],
    extra_compile_args=["-std=c99", "-D_GNU_SOURCE"],
)

setup(
    name="cSigner",
    version="1.0.0",
    description="Sign extension",
    ext_modules=[module],
)