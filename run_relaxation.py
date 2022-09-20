from pathlib import Path
import os
import shutil
import glob

from dflow.python import (OP, OPIO, Artifact, OPIOSign,
                          upload_packages)

from dflow import argo_range

if "__file__" in locals():
    upload_packages.append(__file__)


class RelaxRun(OP):
    def __init__(self):
        pass

    @classmethod
    def get_input_sign(cls):
        return OPIOSign({
            'target_tasks': Artifact(Path)
        })

    @classmethod
    def get_output_sign(cls):
        return OPIOSign({
            'out_tasks': Artifact(Path)
        })

    def run(self, path_to_work):
        os.chdir(path_to_work)
        os.system("lmp -i in.lammps -v restart 0")

    @OP.exec_sign_check
    def execute(
            self,
            op_in: OPIO,
    ) -> OPIO:
        op_out = OPIO({
            "out_tasks": Path('confs')
        })
        structures = op_in['target_tasks']
        conf_dirs = []
        conf_dirs.extend(glob.glob(os.path.join(str(structures),'')))
        print(conf_dirs)
        cwd = os.getcwd()
        for ii in conf_dirs:
            path_to_work = os.path.join(ii,'relaxation/relax_task')
            self.run(path_to_work)
            os.chdir(cwd)
        shutil.copytree(structures, op_out["out_tasks"])
        return op_out


if __name__ == "__main__":
    pass
