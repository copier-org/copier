# -*- coding: utf-8 -*-
b'This library requires Python 2.6, 2.7, 3.3 or newer'
import io
import os
import re
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


PACKAGE = 'voodoo'


def get_path(*args):
    return os.path.join(os.path.dirname(__file__), *args)


def read_from(filepath):
    with io.open(filepath, 'rt', encoding='utf8') as f:
        return f.read()


def get_version():
    data = read_from(get_path(PACKAGE, '__init__.py'))
    version = re.search(r"__version__\s*=\s*u?'([^']+)'", data).group(1)
    return str(version)


def find_package_data(root, include_files=('.gitignore', )):
    files = []
    src_root = get_path(root).rstrip('/') + '/'
    for dirpath, subdirs, filenames in os.walk(src_root):
        path, dirname = os.path.split(dirpath)
        if dirname.startswith(('.', '_')):
            continue
        dirpath = dirpath.replace(src_root, '')
        for filename in filenames:
            is_valid_filename = not (
                filename.startswith('.') or
                filename.endswith('.pyc')
            )
            include_it_anyway = filename in include_files

            if is_valid_filename or include_it_anyway:
                files.append(os.path.join(dirpath, filename))
    return files


def find_packages_data(*roots):
    return dict([(root, find_package_data(root)) for root in roots])


def get_requirements(filename='requirements.txt'):
    data = read_from(get_path(filename))
    lines = map(lambda s: s.strip(), data.splitlines())
    return [l for l in lines if l and not l.startswith('#')]


setup(
    name='Voodoo',
    version=get_version(),
    author='Juan-Pablo Scaletti',
    author_email='juanpablo@lucumalabs.com',
    packages=[PACKAGE],
    package_data=find_packages_data(PACKAGE, 'tests'),
    zip_safe=False,
    url='http://github.com/lucuma/Voodoo',
    license='MIT license (http://www.opensource.org/licenses/mit-license.php)',
    description='Template system for project skeletons',
    long_description=read_from(get_path('README.rst')),
    install_requires=get_requirements(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
