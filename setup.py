import os

from setuptools import setup, find_packages

from pymess.version import get_version


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="django-pymess",
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    version=get_version(),
    description="Pymess is a Django framework for sending messages",
    author='Lubos Matl,Oskar Hollman',
    author_email='matllubos@gmail.com',
    url='https://github.com/druids/django-pymess',
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
        'django>=1.11',
        'django-chamber>=0.5.8',
        'attrdict>=2.0.1',
        'beautifulsoup4==4.8.0',
    ],
    zip_safe=False
)
