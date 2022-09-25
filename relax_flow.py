import time

from dflow import Step, Workflow, download_artifact, upload_artifact
from dflow.python import PythonOPTemplate
from dflow.plugins.dispatcher import DispatcherExecutor

lbg_resource_dict = {
    "number_node": 1,
    "cpu_per_node": 8,
    "gpu_per_node": 1,
    "queue_name": "eosflow_run",
    "group_size": 1,
    "source_list": ["/opt/deepmd-kit-2.0.1"]
    # "source_list": ["/opt/intel/oneapi/setvars.sh"]
}
lbg_machine_dict = {
    "batch_type": "Lebesgue",
    "context_type": "LebesgueContext",
    "local_root": "./",
    "remote_profile": {
        "email": "******",
        "password": "******",
        "program_id": ****,
        "input_data": {
            "api_version": 2,
            "job_type": "indicate",
            "log_file": "log",
            "grouped": True,
            "job_name": "eosflow_run",
            "disk_size": 100,
            "scass_type": "c12_m92_1 * NVIDIA V100",
            "platform": "ali",
            # "image_name":"zhuoyli/dflow_test:eos",
            "image_name": "LBG_DeePMD-kit_2.0.1_v1.1",
            "on_demand": 0
        }
    }
}

def main():
    from relaxation import (RelaxMake, RelaxPost)
    from run_relaxation import RelaxRun
    # define dispatcher
    dispatcher_executor = DispatcherExecutor(
        host="127.0.0.1", port="2746",
        machine_dict=lbg_machine_dict,
        resources_dict=lbg_resource_dict)

    wf = Workflow(name="relax")

    artifact0 = upload_artifact("param_relax.json")
    artifact1 = upload_artifact("POSCAR")
    artifact2 = upload_artifact("frozen_model.pb")
    print(artifact0)
    print(artifact1)
    print(artifact2)
    # print(artifact3)
    step_make = Step(
        name="relax-make",
        template=PythonOPTemplate(RelaxMake, image="zhuoyli/dflow_test:cn"),
        artifacts={"parameters": artifact0,
                   "structure": artifact1,
                   "potential": artifact2},
    )
    artifact_target_tasks = step_make.outputs.artifacts["tasks"]

    step_run = Step(
        name="relax-run",
        template=PythonOPTemplate(RelaxRun,
                                  image="zhuoyli/dflow_test:cn",
                                  command=['python3']),
        artifacts={"target_tasks": artifact_target_tasks}, executor=dispatcher_executor,
        util_command=['python3']
    )
    artifact_out_tasks = step_run.outputs.artifacts["out_tasks"]

    step_post = Step(
        name="relax-post",
        template=PythonOPTemplate(RelaxPost, image="zhuoyli/dflow_test:cn"),
        artifacts={"parameters": artifact0,
                   "result_tasks": artifact_out_tasks}
    )

    wf.add(step_make)
    wf.add(step_run)
    wf.add(step_post)
    wf.submit()

    while wf.query_status() in ["Pending", "Running"]:
        time.sleep(1)

    assert (wf.query_status() == "Succeeded")
    step = wf.query_step(name="relax-post")[0]
    assert (step.phase == "Succeeded")

    download_artifact(step.outputs.artifacts["relaxation_finished"])


if __name__ == "__main__":
    main()
