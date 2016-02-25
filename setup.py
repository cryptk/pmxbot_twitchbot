import setuptools

setup_params = dict(
    name="pmxbot_twitchbot",
    version = "0.0.1",
    packages=setuptools.find_packages(),
    entry_points=dict(
        pmxbot_handlers = [
            'pmxbot_twitchbot = twitchbot',
        ]
    ),
    description="A series of plugins to make pmxbot useful as a twitch.tv channel moderation bot",
    author="Chris Jowett",
    author_email="cryptkbot@gmail.com",
    maintainer = 'Chris Jowett',
    maintainer_email = 'cryptkbot@gmail.com',
    url = 'https://www.cryptkcoding.com',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Communications :: Chat',
        'Topic :: Communications :: Chat :: Internet Relay Chat',
    ],
)

if __name__ == '__main__':
    setuptools.setup(**setup_params)
