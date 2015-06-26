# -*- coding: utf-8 -*-
from fabric.api import env, run, sudo, local, put, settings
import fabtools

def production():
        """Defines production environment"""
        env.hosts = ['192.168.1.2']
        env.shell = 'bash -c'    #интерпретатор для выполнения команд на удаленном хосте
        env.use_ssh_config = True    #импортируем конфигурацию нашего ssh-клиента
        env.project_user = "myappuser"    #пользователь, от которого работает проект на удаленном сервере
        env.sudo_user = env.project_user
        env.base_dir = "/apps"    #базовая директория для проекта
        env.domain_name = "myapp.example.com"    #FQDN для нашего продакшн окружения
        env.domain_path = "%(base_dir)s/%(domain_name)s" % { 'base_dir':env.base_dir, 'domain_name':env.domain_name }    #здесь мы сформировали абсолютное имя каталога для myapp
        env.current_path = "%(domain_path)s/current" % { 'domain_path':env.domain_path }    #путь до текущей версии myapp
        env.releases_path = "%(domain_path)s/releases" % { 'domain_path':env.domain_path }    #путь до каталога с релизами
        env.git_clone = "git@git.example.com:myapp.git"    #репозиторий, откуда мы будем клонировать проект.
        env.config_file = "config/config-production.php"    #конфигурационные параметры для нашего проекта

def permissions():
        """Set proper permissions for release"""
        sudo("chown -R %(project_user)s:%(project_user)s %(domain_path)s" % { 'domain_path':env.domain_path, 'project_user':env.sudo_user })

def setup():
        """Prepares one or more servers for deployment"""
        with settings(sudo_user='root'):
                sudo("mkdir -p %(domain_path)s/releases" % { 'domain_path':env.domain_path })
                sudo("mkdir -p %(base_dir)s/logs/" % { 'base_dir':env.base_dir })
                permissions()
                put("sudoers/devel_sudo", "/tmp/devel_sudo")
                sudo("chown root:root /tmp/devel_sudo")
                sudo("chmod 0440 /tmp/devel_sudo")
                sudo("mv /tmp/devel_sudo /etc/sudoers.d/devel_sudo")

def releases():
        """List a releases made"""
        env.releases = sorted(sudo('ls -x %(releases_path)s' % { 'releases_path':env.releases_path }).split())
        if len(env.releases) >= 1:
                env.current_revision = env.releases[-1]
                env.current_release = "%(releases_path)s/%(current_revision)s" % { 'releases_path':env.releases_path, 'current_revision':env.current_revision }
        if len(env.releases) > 1:
                env.previous_revision = env.releases[-2]
                env.previous_release = "%(releases_path)s/%(previous_revision)s" % { 'releases_path':env.releases_path, 'previous_revision':env.previous_revision }

def restart():
        """Restarts your application services"""
        with settings(sudo_user='root',use_shell=False):
                sudo("/etc/init.d/php5-fpm reload")

def checkout():
        """Checkout code to the remote servers"""
        env.timestamp = run("/bin/date +%s")
        env.current_release = "%(releases_path)s/%(timestamp)s" % { 'releases_path':env.releases_path, 'timestamp':env.timestamp }
        sudo("cd %(releases_path)s; git clone -q -b master --depth 1 %(git_clone)s %(current_release)s" % { 'releases_path':env.releases_path, 'git_clone':env.git_clone, 'current_release':env.current_release })

def copy_config():
        """Copy custom config to the remote servers"""
        if not env.has_key('releases'):    #определяем последний релиз, в который нам надо положить конфиг
                releases()
        put("%s" % env.config_file, "/tmp/config.php")
        sudo("cp /tmp/config.php %(current_release)s/config/" % { 'current_release':env.current_release })
        run("rm /tmp/config.php")

def symlink():
        """Updates the symlink to the most recently deployed version"""
        if not env.has_key('current_release'):
                releases()
        sudo("ln -nfs %(current_release)s %(current_path)s" % { 'current_release':env.current_release, 'current_path':env.current_path })

def deploy():
        """Deploys your project. This calls  'checkout','copy_config','migration','symlink','restart','cleanup'"""
        checkout()
        copy_config()
        symlink()
        restart()

def cleanup():
        """Clean up old releases"""
        if not env.has_key('releases'):
                releases()
        if len(env.releases) > 10:
                directories = env.releases
                directories.reverse()
                del directories[:10]
                env.directories = ' '.join([ "%(releases_path)s/%(release)s" % { 'releases_path':env.releases_path, 'release':release } for release in directories ])
                sudo("rm -rf %(directories)s" % { 'directories':env.directories })

def rollback_code():
        """Rolls back to the previously deployed version"""
        if not env.has_key('releases'):
                releases()
        if env.has_key('previous_release'):
                sudo("ln -nfs %(previous_release)s %(current_path)s && rm -rf %(current_release)s" % { 'current_release':env.current_release, 'previous_release':env.previous_release, 'current_path':env.current_path })
        else:
                print "no releases older then current"
                sys.exit(1)

def rollback():
        """Rolls back to a previous version and restarts"""
        rollback_code()
        restart()
