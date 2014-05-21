# -*- coding: utf-8 -*-
'''
A general map/reduce style salt runner for aggregating results
returned by several different minions.

.. versionadded:: Helium

Aggregated results are sorted by the size of the minion pools which returned
matching results.

Useful for playing the game: " some of these things are not like the others... "
when identifying discrepancies in a large infrastructure managed by salt.
'''

import salt.client


def hash(*args, **kwargs):
    '''
    Return the MATCHING minion pools from the aggregated and sorted results of
    a salt command

    .. versionadded:: Helium

    This command is submitted via a salt runner using the
    general form:

        salt-run survey.hash [survey_sort=up/down] <target>
                  <salt-execution-module> <salt-execution-module parameters>

    Optionally accept a "survey_sort=" parameter. Default: "survey_sort=down"

    CLI Example #1: ( functionally equivalent to "salt-run manage.up" )

    .. code-block:: bash

        salt-run survey.hash "*" test.ping

    CLI Example #2: ( find an "outlier" minion config file )

    .. code-block:: bash

        salt-run survey.hash "*" file.get_hash /etc/salt/minion survey_sort=up
    '''

    bulk_ret = _get_pool_results(*args, **kwargs)
    for k in bulk_ret:
        print 'minion pool :\n' \
              '------------'
        print k['pool']
        print 'pool size :\n' \
              '----------'
        print '    ' + str(len(k['pool']))
        print 'pool result :\n' \
              '-------'
        print '    ' + str(k['result'])
        print '\n'

    return bulk_ret


def diff(*args, **kwargs):
    '''
    Return the DIFFERENCE of the result sets returned by each matching minion
    pool

    .. versionadded:: Helium

    These pools are determined from the aggregated and sorted results of
    a salt command.
    This command displays the "diffs" as a series of 2-way differences-- namely
    the diffence between the FIRST displayed minion pool
    (according to sort order) and EACH SUBSEQUENT minion pool result set.
    Differences are displayed according to the Python "difflib.unified_diff()"
    as in the case of the salt execution module "file.get_diff".

    This command is submitted via a salt runner using the general form:

        salt-run survey.diff [survey_sort=up/down] <target>
                     <salt-execution-module> <salt-execution-module parameters>

    Optionally accept a "survey_sort=" parameter. Default: "survey_sort=down"

    CLI Example #1: ( Example to display the "differences of files" )

    .. code-block:: bash

        salt-run survey.diff survey_sort=up "*" cp.get_file_str file:///etc/hosts
    '''
    # TODO: The salt execution module "cp.get_file_str file:///..." is a
    # non-obvious way to display the differences between files using
    # survey.diff .  A more obvious method needs to be found or developed.

    import difflib

    bulk_ret = _get_pool_results(*args, **kwargs)

    is_first_time = True
    for k in bulk_ret:
        print 'minion pool :\n' \
              '------------'
        print k['pool']
        print 'pool size :\n' \
              '----------'
        print '    ' + str(len(k['pool']))
        if is_first_time:
            is_first_time = False
            print 'pool result :\n' \
                  '------------'
            print '    ' + bulk_ret[0]['result']
            print
            continue

        outs = ('differences from "{0}" results :').format(
            bulk_ret[0]['pool'][0])
        print outs
        print '-' * (len(outs) - 1)
        from_result = bulk_ret[0]['result'].splitlines()
        for i in xrange(0, len(from_result)):
            from_result[i] += '\n'
        to_result = k['result'].splitlines()
        for i in xrange(0, len(to_result)):
            to_result[i] += '\n'
        outs = ''
        outs += ''.join(difflib.unified_diff(from_result,
                                             to_result,
                                             fromfile=bulk_ret[0]['pool'][0],
                                             tofile=k['pool'][0],
                                             n=0))
        print outs
        print

    return bulk_ret


def _get_pool_results(*args, **kwargs):
    '''
    A helper function which returns a dictionary of minion pools along with
    their matching result sets.
    Useful for developing other "survey style" functions.
    Optionally accepts a "survey_sort=up" or "survey_sort=down" kwargs for
    specifying sort order.
    Because the kwargs namespace of the "salt" and "survey" command are shared,
    the name "survey_sort" was chosen to help avoid option conflicts.
    '''
    # TODO: the option "survey.sort=" would be preferred for namespace
    # separation but the kwargs parser for the salt-run command seems to
    # improperly pass the options containing a "." in them for later modules to
    # process. The "_" is used here instead.

    import hashlib

    tgt = args[0]
    cmd = args[1]

    sort = kwargs.get('survey_sort', 'down')
    direction = sort != 'up'

    client = salt.client.get_local_client(__opts__['conf_file'])
    minions = client.cmd(tgt, cmd, args[2:], timeout=__opts__['timeout'])
    ret = {}
    # hash minion return values as a string
    for minion in sorted(minions):
        h = hashlib.sha256(str(minions[minion])).hexdigest()
        if not h in ret:
            ret[h] = {}
            ret[h]['pool'] = []
            ret[h]['result'] = str(minions[minion])

        ret[h]['pool'].append(minion)

    sorted_ret = []
    for k in sorted(ret, key=lambda k: len(ret[k]['pool']), reverse=direction):
        # return aggregated results, sorted by size of the hash pool

        sorted_ret.append(ret[k])

    return sorted_ret