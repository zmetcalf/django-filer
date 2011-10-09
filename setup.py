from setuptools import setup, find_packages


setup(
    name = "django-filer",
    version = ":versiontools:filer:",
    url = 'http://github.com/stefanfoulis/django-filer',
    license = 'BSD',
    platforms=['OS Independent'],
    description = "A file management application for django that makes handling of files and images a breeze.",
    long_description = open('README.rst').read(),
    author = 'Stefan Foulis',
    author_email = 'stefan.foulis@gmail.com',
    packages=find_packages(),
    setup_requires = ['versiontools >= 1.8'],
    install_requires = ['easy-thumbnails >= 1.0-alpha-17', 'django-mptt >= 0.2.1', 'django_polymorphic'],
    include_package_data=True,
    zip_safe=False,
    classifiers = [
        'Development Status :: 4 - Beta',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
    ]
)
