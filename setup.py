'''
Created on 16 Nov 2017

@author: Paolo
'''

from setuptools import setup
setup(
    name='mqtt_gateways',
    version='0.1',
    package_dir={'':'mqtt_gateways'},
    packages=['gateway','dummy'],
    install_requires=['paho-mqtt >= 1.3','pySerial >= 3.4'],
    package_data={'dummy': ['data/*.map', 'data/*.conf']},
    exclude_package_data={'': ['README.*']},
#    entry_points={'console_scripts': ['dummy2mqtt = mqtt_gateways.dummy.dummy2mqtt:__main__']},
    
    # metadata for upload to PyPI
    author='Pier Paolo Taddonio',
    author_email='paolo.taddonio@empiluma.com',
    description='Framework for MQTT Gateways',
    license='MIT',
    keywords='mqtt gateway',
    url='http://empiluma.com/mqtt_gateways/',
)