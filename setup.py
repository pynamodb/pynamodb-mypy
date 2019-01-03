from setuptools import find_packages
from setuptools import setup

setup(
    name='pynamodb-mypy',
    version='0.0.1',
    description='mypy plugin for PynamoDB',
    url='https://www.github.com/lyft/pynamodb-mypy',
    maintainer='Ilya Konstantinov',
    maintainer_email='ilya.konstantinov@gmail.com',
    packages=find_packages(exclude=['tests/*']),
    install_requires=[
        'mypy>=0.660',
    ],
    python_requires='>=3',
)
