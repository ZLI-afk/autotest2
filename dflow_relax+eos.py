import time
from monty.serialization import loadfn, dumpfn

from dflow import Step, Workflow, download_artifact, upload_artifact, argo_range
from dflow.python import (PythonOPTemplate, Slices)
from dflow.plugins.dispatcher import DispatcherExecutor


def main():
    from relaxation import (RelaxMake, RelaxPost)
    from Eos import (EosMake, EosPost)
    from run_relaxation import RelaxRun
    from run_property import PropertyRun
    # define dispatcher
    #dispatcher_executor = DispatcherExecutor(
    #    host="127.0.0.1", port="2746",
    #    machine_dict=lbg_machine_dict,
    #    resources_dict=lbg_resource_dict)

    wf = Workflow(name="relax")

    artifact0 = upload_artifact("param_relax.json")
    artifact1 = upload_artifact("confs")
    artifact2 = upload_artifact("frozen_model.pb")
    artifact3 = upload_artifact("param_prop.json")
    artifact4 = upload_artifact("machine.json")
    print(artifact0)
    print(artifact1)
    print(artifact2)
    print(artifact3)
    print(artifact4)

    dispatcher_executor = DispatcherExecutor(
        host="127.0.0.1", port="2746",
        machine_dict=loadfn("machine.json")["lbg_machine_dict"],
        resources_dict=loadfn("machine.json")["lbg_resource_dict"])

    #os.system("tar -xzvf confs.tar.gz")

    relax_make = Step(
        name="relax-make",
        template=PythonOPTemplate(RelaxMake, image="zhuoyli/dflow_test:local_cn"),
        artifacts={"parameters": artifact0,
                   "relaxdir": artifact1,
                   "potential": artifact2},
    )
    artifact_target_tasks = relax_make.outputs.artifacts["tasks"]
    #artifact_task_list = relax_make.outputs.artifacts["tasklist"]

    #relax_run = Step(
    #    name="relax-run",
    #    template=PythonOPTemplate(RelaxRun,
    #                              image="zhuoyli/dflow_test:local_cn",
    #                              command=['python3']),
    #    artifacts={"target_tasks": artifact_target_tasks}, executor=dispatcher_executor,
    #    util_command=['python3']
    #)

    relax_run = Step(
        name="relax-run",
        template=PythonOPTemplate(RelaxRun, slices=Slices("{{item}}", input_artifact=["target_tasks"]),
                                  image="zhuoyli/dflow_test:local_cn",
                                  command=['python3']),
        artifacts={"target_tasks":""}, with_param=argo_range(2), key="dflow-autotest-{{item}}", executor=dispatcher_executor,
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
    relaxmake_step = wf.query_step(name="relax-make")[0]
    assert (relaxmake_step.phase == "Succeeded")
    download_artifact(relaxmake_step.outputs.artifacts["tasks"])


    assert (wf.query_status() == "Succeeded")
    final_step = wf.query_step(name="post-eos")[0]
    assert (final_step.phase == "Succeeded")

    download_artifact(final_step.outputs.artifacts["result_json"])
    download_artifact(final_step.outputs.artifacts["result_out"])


if __name__ == "__main__":
    main()
