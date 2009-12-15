import os, logging
from ConfigParser import NoSectionError, NoOptionError

from gitosis import group
from gitosis.my_fnmatch import fnmatch

def haveAccess(config, user, mode, path):
    """
    Map request for write access to allowed path.

    Note for read-only access, the caller should check for write
    access too.

    Returns ``None`` for no access, or a tuple of toplevel directory
    containing repositories and a relative path to the physical repository.
    """
    log = logging.getLogger('gitosis.access.haveAccess')

    log.debug(
        'Access check for %(user)r as %(mode)r on %(path)r...'
        % dict(
        user=user,
        mode=mode,
        path=path,
        ))

    basename, ext = os.path.splitext(path)
    if ext == '.git':
        log.debug(
            'Stripping .git suffix from %(path)r, new value %(basename)r'
            % dict(
            path=path,
            basename=basename,
            ))
        path = basename

    for groupname in group.getMembership(config=config, user=user):
        try:
            repos = config.get('group %s' % groupname, mode)
        except (NoSectionError, NoOptionError):
            repos = []
        else:
            repos = repos.split()

        mapping = None

        # fnmatch provide glob match support. Jiang Xin <jiangxin net AT ossxp.com>
        for r in repos:
            if fnmatch(path, r):
                log.debug(
                    'Access ok for %(user)r as %(mode)r on %(path)r'
                    % dict(
                    user=user,
                    mode=mode,
                    path=path,
                    ))
                mapping = path
                break
        if mapping is None:
            try:
                for option in config.options('group %s' % groupname):
                    if not option.startswith('map'):
                        continue
                    if fnmatch('map %s %s' % (mode, path), option):
                        mapping = config.get('group %s' % groupname, option)
                        break
            except (NoSectionError, NoOptionError):
                pass
            else:
                log.debug(
                    'Access ok for %(user)r as %(mode)r on %(path)r=%(mapping)r'
                    % dict(
                    user=user,
                    mode=mode,
                    path=path,
                    mapping=mapping,
                    ))

        if mapping is not None:
            prefix = None
            try:
                prefix = config.get(
                    'group %s' % groupname, 'repositories')
            except (NoSectionError, NoOptionError):
                try:
                    prefix = config.get('gitosis', 'repositories')
                except (NoSectionError, NoOptionError):
                    prefix = 'repositories'

            log.debug(
                'Using prefix %(prefix)r for %(path)r'
                % dict(
                prefix=prefix,
                path=mapping,
                ))
            return (prefix, mapping)

# vim: et sw=4 ts=4
