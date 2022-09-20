import time

from dflow import Step, Workflow, download_artifact, upload_artifact
from dflow.python import PythonOPTemplate
from dflow.plugins.dispatcher import DispatcherExecutor

lbg_resource_dict = {
    "number_node": 1,
    "cpu_per_node": 8,
    "gpu_per_node": 1,
    "queue_name": "dflow_run",
    "group_size": 1,
    "source_list": ["/opt/deepmd-kit-2.0.1"]
    # "source_list": ["/opt/intel/oneapi/setvars.sh"]
}
lbg_machine_dict = {
    "batch_type": "Lebesgue",
    "context_type": "LebesgueContext",
    "local_root": "./",
    "remote_profile": {
        "email": "tongqwen@hku.hk",
        "password": "D62Bg31b,",
        "program_id": 1734,
        "input_data": {
            "api_version": 2,
            "job_type": "indicate",
            "log_file": "log",
            "grouped": True,
            "job_name": "dflow_run",
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
    from Eos import (EosMake, EosPost)
    from run_relaxation import RelaxRun
    from run_property import PropertyRun
    # define dispatcher
    dispatcher_executor = DispatcherExecutor(
        host="127.0.0.1", port="2746",
        machine_dict=lbg_machine_dict,
        resources_dict=lbg_resource_dict)

    wf = Workflow(name="relax")

    artifact0 = upload_artifact("param_relax.json")
    artifact1 = upload_artifact("POSCAR")
    artifact2 = upload_artifact("frozen_model.pb")
    artifact3 = upload_artifact("param_prop.json")
    print(artifact0)
    print(artifact1)
    print(artifact2)
    print(artifact3)

    relax_make = Step(
        name="relax-make",
        template=PythonOPTemplate(RelaxMake, image="zhuoyli/dflow_test:local_cn"),
        artifacts={"parameters": artifact0,
                   "structure": artifact1,
                   "potential": artifact2},
    )
    artifact_target_tasks = relax_make.outputs.artifacts["tasks"]

    relax_run = Step(
        name="relax-run",
        template=PythonOPTemplate(RelaxRun,
                                  image="zhuoyli/dflow_test:cn",
                                  command=['python3']),
        artifacts={"target_tasks": artifact_target_tasks}, executor=dispatcher_executor,
        util_command=['python3']
    )
    artifact_out_tasks = relax_run.outputs.artifacts["out_tasks"]

    relax_post = Step(
        name="relax-post",
        template=PythonOPTemplate(RelaxPost, image="zhuoyli/dflow_test:local_cn"),
        artifacts={"parameters": artifact0,
                   "result_tasks": artifact_out_tasks}
    )
    artifact_relaxation = relax_post.outputs.artifacts["relaxation_finished"]

    # define Steps for make, run and post
    eos_make = Step(
        name="make-eos",
        template=PythonOPTemplate(EosMake, image="zhuoyli/dflow_test:local_cn"),
        artifacts={"parameters": artifact3,
                   "relaxation": artifact_relaxation,
                   "potential": artifact2},
    )
    artifact_target_tasks_eos = eos_make.outputs.artifacts["tasks"]

    eos_run = Step(
        name="run-eos",
        template=PythonOPTemplate(PropertyRun,
                                  image="zhuoyli/dflow_test:local_cn",
                                  command=['python3']),
        artifacts={"target_tasks": artifact_target_tasks_eos}, executor=dispatcher_executor,
        util_command=['python3']
    )
    artifact_out_tasks_eos = eos_run.outputs.artifacts["out_tasks"]

    eos_post = Step(
        name="post-eos",
        template=PythonOPTemplate(EosPost, image="zhuoyli/dflow_test:local_cn"),
        artifacts={"result_tasks": artifact_out_tasks_eos}
    )

    wf.add(relax_make)
    wf.add(relax_run)
    wf.add(relax_post)
    wf.add(eos_make)
    wf.add(eos_run)
    wf.add(eos_post)
    wf.submit()

    while wf.query_status() in ["Pending", "Running"]:
        time.sleep(1)

    assert (wf.query_status() == "Succeeded")
    final_step = wf.query_step(name="post-eos")[0]
    assert (final_step.phase == "Succeeded")

    download_artifact(final_step.outputs.artifacts["result_json"])
    download_artifact(final_step.outputs.artifacts["result_out"])


if __name__ == "__main__":
    main()
