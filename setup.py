from setuptools import setup, find_packages

from pymess.version import get_version


setup(
    name="django-pymess",
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
        'django>=1.8',
        'django-chamber>=0.3.7',
        'attrdict>=2.0.0',
        'beautifulsoup4==4.6.0',
    ],
    dependency_links=[
        'https://github.com/druids/django-chamber/tarball/0.3.7#egg=django-chamber-0.3.7'
    ],
    zip_safe=False
)
