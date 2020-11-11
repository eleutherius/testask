#********************************************************************
#**** IMPORT ********************************************************
#********************************************************************
import os,argparse
from testcase.settings import Settings




#********************************************************************
#**** DEFAULT *******************************************************
#********************************************************************
defaultsource = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
defaultsource = os.path.join(defaultsource,'default.json')
defaultsource = os.path.abspath(defaultsource)
config = Settings()
config . read(defaultsource)
# ipmp/browser parameters
configuration = config.items('connection')
configuration = dict(configuration)
# SSH access paramters
ssh = config.items('sshaccess')
ssh = dict(ssh)




#********************************************************************
#**** ARGUMENTS *****************************************************
#********************************************************************
class Arguments(argparse.ArgumentParser) :



    def __init__( self, *arguments, **keywords ) :
        super(Arguments,self).__init__(*arguments,**keywords)
        self.add_argument('-hostname', type = str, default = configuration['hostname'], help = 'Powermanage host. Default is %(default)s.')
        self.add_argument('-username', type = str, default = configuration['username'], help = 'Superadmin email. Default is %(default)s.')
        self.add_argument('-password', type = str, default = configuration['password'], help = 'Superadmin passw. Default is %(default)s.')
        self.add_argument('-sshuser', type = str, default = ssh['sshuser'], help = 'SSH user. Default is %(default)s.')
        self.add_argument('-sshpwd', type = str, default = ssh['sshpwd'], help = 'SSH user password. Default is %(default)s.')
