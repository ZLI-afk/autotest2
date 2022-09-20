from pathlib import Path
from dflow.python import (OP, OPIO, Artifact, OPIOSign, upload_packages)

import os
import shutil
import glob

from monty.serialization import loadfn
from dpgen.auto_test.common_equi import (make_equi, post_equi)

if "__file__" in locals():
    upload_packages.append(__file__)


class RelaxMake(OP):
    def __init__(self):
        pass

    @classmethod
    def get_input_sign(cls):
        return OPIOSign({
            'parameters': Artifact(Path),
            'relaxdir': Artifact(Path),
            'potential': Artifact(Path)
        })

    @classmethod
    def get_output_sign(cls):
        return OPIOSign({
            'inter': dict,
            'relax': dict,
            #'tasklist': Artifact([Path]),
            'tasks': Artifact(Path)
        })
    
    @OP.exec_sign_check
    def execute(
            self,
            op_in: OPIO,
    ) -> OPIO:
        structures = [os.path.join(str(op_in['relaxdir'].parent),loadfn(op_in['parameters'])["structures"][0])]
        conf_dirs = []
        for conf in structures:
            conf_dirs.extend(glob.glob(conf))
        conf_dirs.sort()

        op_out = OPIO({
            "inter": loadfn(op_in['parameters'])["interaction"],
            "relax": loadfn(op_in['parameters'])["relaxation"],
            "tasks": Path("confs"),
            #"tasklist": list(Path("confs").glob('*'))
            #"tasklist": glob.glob("confs/*")
        })

        inter_parameter = loadfn(op_in['parameters'])["interaction"]
        relax_param = loadfn(op_in['parameters'])["relaxation"]

        cwd = os.getcwd()
        make_equi(structures, inter_parameter, relax_param)

        for ii in conf_dirs:
            relaxation = os.path.join(ii, 'relaxation')
            relax_task = os.path.join(relaxation, 'relax_task')
            os.chdir(relaxation)
            if os.path.islink('frozen_model.pb'):
                os.remove('frozen_model.pb')
            shutil.copyfile(op_in['potential'], 'frozen_model.pb')
            os.chdir(relax_task)
            if os.path.islink('frozen_model.pb') and os.path.islink('POSCAR'):
                os.remove('frozen_model.pb')
                os.remove('POSCAR')
            shutil.copyfile(op_in['potential'], 'frozen_model.pb')
            shutil.copyfile('../../POSCAR', 'POSCAR')
            os.chdir(cwd)
            #shutil.copytree(relaxtaion, 'relaxation')
        shutil.copytree(op_in['relaxdir'], 'confs')

        return op_out


class RelaxPost(OP):
    def __init__(self):
        pass

    @classmethod
    def get_input_sign(cls):
        return OPIOSign({
            'result_tasks': Artifact(Path),
            'parameters': Artifact(Path)
        })

    @classmethod
    def get_output_sign(cls):
        return OPIOSign({
            #'result_json': Artifact(Path),
            'relaxation_finished': Artifact(Path)
        })

    @OP.exec_sign_check
    def execute(
            self,
            op_in: OPIO,
    ) -> OPIO:
        op_out = OPIO({
            #"result_json": Path("result.json"),
            "relaxation_finished": Path("confs")
        })
        structures = [os.path.join(str(op_in['result_tasks'].parent),loadfn(op_in['parameters'])["structures"][0])]
        #confs = [str(op_in["result_tasks"].parent)]
        inter_param = loadfn(op_in['parameters'])["interaction"]

        cwd = os.getcwd()
        post_equi(structures, inter_param)
        os.chdir(cwd)
        shutil.copytree(op_in["result_tasks"], 'confs')

        return op_out


if __name__ == "__main__":
    pass
