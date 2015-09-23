import os
from setuptools import setup

current_dir = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(current_dir, 'README.md')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-deployment',
    version='0.1.4.3',
    packages=['deployment'],
    include_package_data=True,
    license='GPL v3 License',  # example license
    description='A simple deployment Django library using Fabric and Chef',
    long_description=README,
    url='http://www.example.com/',
    author='Jean-Mark Wright',
    author_email='jeanmark.wright@gmail.com',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License', # example license
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        # Replace these appropriately if you are stuck on Python 2.
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    install_requires=[ req for req in open("%s/requirements.txt" % current_dir,"r").read().splitlines() if req.strip() and not req.startswith("#")]
)