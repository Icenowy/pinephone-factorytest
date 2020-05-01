from setuptools import setup

setup(
    name='factorytest_pinephone',
    version='0.44.0',
    packages=['factorytest', 'factorytest.ioctl', 'factorytest.bmap'],
    url='https://gitlab.com/MartijnBraam/factorytest',
    license='MIT',
    author='Martijn Braam',
    author_email='martijn@brixit.nl',
    description='Factory test tool for the PinePhone',
    long_description=open("README.rst").read(),
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
        'Operating System :: POSIX :: Linux',
    ],
    install_requires=[
        'wifi',
        'smbus',
        'pyserial'
    ],
    zip_safe=True,
    include_package_data=True,
    entry_points={
        'gui_scripts': [
            'factorytest=factorytest.__main__:main'
        ]
    }
)
