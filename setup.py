from setuptools import setup

setup(
    name='whalesharkiiot',
    version='0.0.1',
    description='whalesharkiiot pip install',
    url='https://github.com/dataignitelab/WhaleShark_IIoT.git',
    author='theprismdata',
    author_email='theprismdata@gmail.com',
    license='Apache2.0',
    package=['WhaleShark_IIoT'],
    zip_safe=False,
    install_requires=[
        'astroid==2.4.2',
        'asyncio==3.4.3',
        'certifi==2020.6.20',
        'chardet==3.0.4',
        'flake8==3.8.3',
        'httplib2==0.18.1',
        'idna==2.9',
        'influxdb==5.3.0',
        'isort==4.3.21',
        'lazy-object-proxy==1.4.3',
        'mccabe==0.6.1',
        'minimalmodbus==1.0.2',
        'msgpack==0.6.1',
        'pika==1.1.0',
        'pycodestyle==2.6.0',
        'pyflakes==2.2.0',
        'pyserial==3.4',
        'python-dateutil==2.8.1',
        'pytz==2020.1',
        'PyYAML==5.3.1',
        'rabbitmq-admin==0.2',
        'redis==3.5.3',
        'requests==2.24.0',
        'Rx==3.1.0',
        'toml==0.10.1',
        'urllib3==1.25.10',
        'wrapt==1.12.1'
    ]
)