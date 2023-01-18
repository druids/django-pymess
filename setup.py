import os

from setuptools import setup, find_packages

from pymess.version import get_version


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="skip-django-pymess",
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    version=get_version(),
    description="Pymess is a Django framework for sending messages",
    author='Lubos Matl,Oskar Hollman',
    author_email='matllubos@gmail.com',
    url='https://github.com/skip-pay/django-pymess',
    license='LGPL',
    package_dir={'pymess': 'pymess'},
    include_package_data=True,
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
    ],
    install_requires=[
        'django>=3.1',
        'skip-django-chamber>=0.6.16.3',
        'beautifulsoup4==4.8.0',
        'skip-django-choice-enumfields>=1.1.3.2',
    ],
    zip_safe=False
)
