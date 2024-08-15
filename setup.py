import sys
from setuptools import setup, find_packages

# Common dependencies
common_dependencies = [
    'meshtastic',
    'pyserial',
    'pynput',
    'pyfiglet',
    'bleak',  
]

# Platform-specific dependencies
if sys.platform.startswith('win'):
    platform_dependencies = [
        'pywin32',
        'pygetwindow',
    ]
elif sys.platform.startswith('linux'):
    platform_dependencies = [
        'python3-xlib',
        'python3-tk',
        'python3-dev',
        'xdotool',
    ]
else:
    platform_dependencies = []

setup(
    name='K3ANO-NewNodes',
    version='0.86',
    packages=find_packages(),
    description='A tool for processing new nodes in Meshtastic networks',
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/StevoKeano/meshtastic-new-node-processing',
    author='StevoKeano',
    author_email='ppsel03@gmail.com',
    license='MIT',
    install_requires=common_dependencies,
    extras_require={
        'windows': platform_dependencies if sys.platform.startswith('win') else [],
        'linux': platform_dependencies if sys.platform.startswith('linux') else [],
    },
    entry_points={
        'console_scripts': [
            'K3ANO_NewNodes=K3ANO_NewNodes.newNode:main',
            'K3ANO-NewNodes=K3ANO_NewNodes.newNode:main',
            'NewNodes=K3ANO_NewNodes.newNode:main',
        ],
    },
    package_data={
        'K3ANO_NewNodes': ['settings.json', 'nodes.txt', 'traceroute_log.txt'],
    },
    exclude_package_data={
        '': ['.vs', '__pycache__', '*.pyc'],
        'K3ANO_NewNodes': ['.vs', '__pycache__', '*.pyc'],
    },
    include_package_data=True,
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
    ],
    python_requires='>=3.6',
)