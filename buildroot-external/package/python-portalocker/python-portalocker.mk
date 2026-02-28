################################################################################
#
# python-portalocker
#
################################################################################

PYTHON_PORTALOCKER_VERSION = 2.0.0
PYTHON_PORTALOCKER_SOURCE = portalocker-$(PYTHON_PORTALOCKER_VERSION).tar.gz
PYTHON_PORTALOCKER_SITE = https://files.pythonhosted.org/packages/df/48/62cf97ff7d2233e7db29dfb83f1584e26289e88af8af39de1a76629ac487
PYTHON_PORTALOCKER_SETUP_TYPE = setuptools
PYTHON_PORTALOCKER_LICENSE = BSD-3-Clause
PYTHON_PORTALOCKER_LICENSE_FILES = LICENSE

$(eval $(python-package))
