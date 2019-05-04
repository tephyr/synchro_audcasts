#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author:  Andrew Ittner <aji@rhymingpanda.com>
# Purpose: Synchronize the audcast directory on a computer with an audio player
# Created: 2010-05-15
"""
Purpose: Synchronize the audcast directory on a computer with an audio player
"""

import os
import shutil
import logging
import argparse
from pathlib import Path


class Synchronizer(object):
    """Synchronizes any audcast-containing directory 
    against an audio player's directory
    Checks for mount issues, disk space, and deleted files
    """
    
    def __init__(self, hostpath, hostarchive, 
                 playermount, playerpath, 
                 playerpatharchive, playerpathdelete):
        self.hostpath = hostpath
        self.hostarchive = hostarchive
        self.playermount = playermount
        self.playerpath = playerpath
        self.playerpatharchive = playerpatharchive
        self.playerpathdelete = playerpathdelete
        
        # begin logging
        self.prep_logging()

    def prep_logging(self):
        """setup logging"""
        logging.basicConfig(level=logging.INFO,
                            format='%(levelname)-8s %(message)s',
                            datefmt='%H:%M:%S',
                            )

    def validate_paths(self):
        """check that paths exist and target is mounted
        Return: t/f"""
        logging.debug('checking that all paths exists')
        # host exists?
        self._path_host = Path(self.hostpath).expanduser()
        assert isinstance(self._path_host, Path)
        if not _path_validator(self._path_host,
                               'Host path (%s) does not exist'):
            return False

        # host archive exists?
        self._path_host_archive = Path(self.hostarchive).expanduser()
        assert isinstance(self._path_host_archive, Path)
        if not _path_validator(self._path_host_archive,
                               'Host archive path (%s) does not exist'):
            return False
        
        # player mount exists?
        self._path_playermount = Path(self.playermount).expanduser()
        assert isinstance(self._path_playermount, Path)
        if not _path_validator(self._path_playermount,
                               'Target mount path (%s) does not exist'):
            return False
        
        # player mount is mounted?
        if not os.path.ismount(self._path_playermount):
            logging.warn('Target mount path (%s) is not mounted', 
                         self._path_playermount.absolute())
            return False
        
        # player path exists?
        self._path_playerpath = Path(self.playerpath).expanduser()
        assert isinstance(self._path_playerpath, Path)
        if not _path_validator(self._path_playerpath,
                               'Target path (%s) does not exist'):
            return False

        # player archive path exists?
        self._path_playerpath_archive = Path(self.playerpatharchive).expanduser()
        assert isinstance(self._path_playerpath_archive, Path)
        if not _path_validator(self._path_playerpath_archive,
                               'Player archive path (%s) does not exist'):
            return False
        
        # player delete path exists?
        self._path_playerpath_delete = Path(self.playerpathdelete).expanduser()
        assert isinstance(self._path_playerpath_delete, Path)
        if not _path_validator(self._path_playerpath_delete,
                               'Player delete path (%s) does not exist'):
            return False
        
        return True
    
    def run(self, debug=False):
        """
        Run the entire process
        """
        # set logging level
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # validate all paths
        if not self.validate_paths():
            logging.warn('Path validation failed; aborting')
            return False
        
        # prep counts
        count_archived_files = 0
        count_deleted_files = 0
        count_copied_files = 0
        
        # for all files in playerpatharchive, move to host
        for p in self._path_playerpath_archive.iterdir():
            if not (p.is_file() and not p.is_symlink()):
                continue
            # is this in host? if so, move
            host_archive_candidate = Path(self._path_host, 
                                          p.name)
            logging.debug('Will archive %s',
                          host_archive_candidate.absolute())
            if not debug:
                print('ARCHIVE %s' % p.name)
                if host_archive_candidate.exists():
                    # move on host; remove from player
                    shutil.move(str(host_archive_candidate), str(self._path_host_archive))
                    p.unlink()
                else:
                    # player has an archived file that doesn't exist on host
                    shutil.move(str(p), str(self._path_host_archive))
                    
            count_archived_files += 1
        
        # for all files in playerpath/delete, delete from host
        path_player_delete = Path(self._path_playerpath, 'delete')
        for p in path_player_delete.iterdir():
            if not (p.is_file() and not p.is_symlink()):
                continue
            path_host_to_remove = Path(self._path_host, p.name)
            if path_host_to_remove.exists():
                logging.debug('Will remove %s', 
                              path_host_to_remove.absolute())
                if not debug:
                    path_host_to_remove.unlink()
                
            if not debug:
                print('REMOVE %s' % p)
                p.unlink()
            count_deleted_files += 1
            
        # for all files in host, verify they exist in target
        for p in self._path_host.iterdir():
            if not (p.is_file() and not p.is_symlink()):
                continue
            path_player = Path(self._path_playerpath, p.name)
            if not path_player.exists():
                if not _space_checker(self._path_playermount,
                                      p):
                    logging.warn('Not enough space for %s; aborting',
                                 p.absolute())
                    break
                logging.debug("Will copy %s", p.name)
                # check for space
                if not debug:
                    print("COPY %s" % p.name)
                    shutil.copy(str(p), str(path_player))
                count_copied_files += 1
        
        logging.info('Archived %s files, removed %s files, copied %s files', 
                     count_archived_files,
                     count_deleted_files,
                     count_copied_files)
        
        return True

    
def _space_checker(mount_to_check, file_to_check):
    """given a mount point and a file, check if the mount point has enough
    space for the given file
    Returns t/f"""
    statinfo = os.statvfs(mount_to_check)
    
    block_size = statinfo.f_frsize
    available_blocks = statinfo.f_bavail
    bytes_available = block_size * available_blocks
    
    file_size = Path(file_to_check).stat().st_size
    
    return bytes_available >= file_size
    

def _path_validator(path_to_check, warning_message):
    """checks for existing Path()
    Returns t/f"""
    if not path_to_check.exists():
        logging.warn(warning_message, path_to_check.absolute())
        return False
    return True
    

def run():
    """run helper; sets up class & runs it"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--host',
                      dest='host',
                      help='host path')
    parser.add_argument('--host-archive',
                      dest='host_archive',
                      help="full path to host's archive")
    parser.add_argument('--player-mount',
                      dest='player_mount',
                      help="full path to player's mount point")
    parser.add_argument('--player-path',
                      dest='player_path',
                      help="full path to player's storage directory")
    parser.add_argument('--player-archive',
                      dest='player_archive',
                      help="full path to player's archive directory")
    parser.add_argument('--player-delete',
                      dest='player_delete',
                      help="full path to player's delete directory")
    parser.add_argument("-d", "--debug", 
                      dest="debug",
                      action="store_true",
                      help="debug mode (NO filesystem changes)")
    parser.add_argument("-v", "--verbose",
                      action="store_true", dest="verbose")
    args = parser.parse_args()

    synchro = Synchronizer(args.host, args.host_archive, 
                           args.player_mount, args.player_path, 
                           args.player_archive, args.player_delete,)
    synchro.run(args.debug)

if __name__ == '__main__':
    run()
