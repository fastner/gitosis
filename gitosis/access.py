import os, logging
import re
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

    synonyms = {}
    synonyms['read'] = ['readonly', 'readable']
    synonyms['write'] = ['writable', 'writeable']
    synonyms['init'] = ['initial']

    mode_syns = []
    for key, mode_syns in synonyms.items():
        if mode == key:
            break
        elif mode in mode_syns:
            if mod != mode_syns[0]:
                log.warning(
                    'Provide haveAccess with mode: "'
                    + mode + '" '
                    + 'for repository %r should be "' + key +'"',
                    path,
                    )
            mode = key
            break
    if key != mode:
        log.warning('Unknown acl mode %s, check gitosis config file.' % mode)
        mode_syns = [mode]
    else:
        mode_syns.append(mode)


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
        repos = ""
        try:
            options = config.options('group %s' % groupname)
            for syn in mode_syns:
                if syn in options:
                    if syn != mode and syn != mode_syns[0]:
                        log.warning(
                            'Repository %r config has typo "'
                            + syn + '", '
                            +'should be "' + mode +'"',
                            path,
                            )
                    repos = config.get('group %s' % groupname, syn)
                    break
        except (NoSectionError, NoOptionError):
            repos = []
        else:
            repos = repos.split()

        mapping = None

        # fnmatch provide glob match support. Jiang Xin <jiangxin AT ossxp.com>
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
                    (_ignore, opt_right) = option.split(' ',1)
                    (opt_mode, opt_path) = opt_right.strip().split(' ',1)
                    opt_path = opt_path.strip()
                    if opt_mode not in mode_syns:
                        continue
                    if fnmatch(path, opt_path):
                        mapping = config.get('group %s' % groupname, option)
                        if ':' in mapping:
                            (opt_from, opt_to) = mapping.split(':',1)
                            mapping = re.sub(opt_from, opt_to, path)
                        elif '\\1' in mapping:
                            mapping = mapping.replace('\\1', path)
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
            return (prefix, mapping, mode)

# vim: et sw=4 ts=4
