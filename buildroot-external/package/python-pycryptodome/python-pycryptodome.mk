################################################################################
#
# python-pycryptodome
#
################################################################################

PYTHON_PYCRYPTODOME_VERSION = 3.9.8
PYTHON_PYCRYPTODOME_SOURCE = pycryptodome-$(PYTHON_PYCRYPTODOME_VERSION).tar.gz
PYTHON_PYCRYPTODOME_SITE = https://files.pythonhosted.org/packages/4c/2b/eddbfc56076fae8deccca274a5c70a9eb1e0b334da0a33f894a420d0fe93
PYTHON_PYCRYPTODOME_SETUP_TYPE = setuptools
PYTHON_PYCRYPTODOME_LICENSE = BSD-2-Clause, Public Domain
PYTHON_PYCRYPTODOME_LICENSE_FILES = LICENSE.rst

PYTHON_PYCRYPTODOME_ENV = CFLAGS="$(TARGET_CFLAGS) -std=c99"

$(eval $(python-package))
