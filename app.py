import streamlit as st
import elytica_dss as edss
import time
import json
import pandas as pd

dss = edss.Service(st.secrets["elytica"]["token"])
dss.login()
st.write("# Optimize your diet")
projects = dss.getProjects()
name="Diet Problem"
description="The diet problem"
project = list(filter(lambda p: p.name == name, projects)) 
job = None
job_completed = False
output=""
input_filename="diet_problem.json"
latex_out = ""
results = ""

def selectJob(project):
  dss.selectProjectById(project.id)
  jobs = dss.getJobs()
  job = jobs[0]
  dss.selectJobById(job.id)
  return job

if not project:
  st.write("No project named Diet. Please proceed to create a project.")
  applications = dss.getApplications()
  option = st.selectbox(
      'What type of application should the diet problem be?',
      tuple([a.display_name for a in applications]))
  if st.button('Create Project'):
    app = [a for a in applications if a.display_name==option][0]
    projects = dss.createProject(name, description, app)
    project = list(filter(lambda p: p.name == name, projects))[0] 
    job = selectJob(project)
else:
  project = project[0]
  job = selectJob(project)

input_files = dss.getInputFiles()

def assignAndUploadFile(name, contents, arg, replace=True):
  file = list(filter(lambda f: f.name == name, input_files))
  if not file or replace:
    input_file = dss.uploadFileContents(name, contents)
    dss.assignFile(input_file, arg)


with open(input_filename, 'r') as f:
  diet_data = json.load(f)

food_edited_df = st.experimental_data_editor( pd.DataFrame(diet_data["Food"]), num_rows="dynamic")
nutrients_edited_df = st.experimental_data_editor(pd.DataFrame(diet_data["Nutrients"]), num_rows="dynamic")

if st.button('Save'):
  diet_data["Food"] = json.loads(food_edited_df.to_json(orient="records"))
  diet_data["Nutrients"] = json.loads(nutrients_edited_df.to_json(orient="records"))
  with open(input_filename, 'w') as f:
    json.dump(diet_data, indent=2, ensure_ascii=False, fp=f) 

def getStdOut(data):
  global output
  output = output + json.loads(data)['stdout'].replace("\n", " \n\r ")

def finished(data):
  global job_completed, latex_out, results
  output_files = dss.getOutputFiles()
  for f in output_files:
    if f.name == "latex_out":
      latex_out = dss.downloadFile(f) 
    if f.name == "results":
      results = dss.downloadFile(f)
  job_completed = True

if st.button('Run'):
  model = open('model.hlpl', 'r').read()
  assignAndUploadFile(f"{job.id}.hlpl", model, 1, replace=False)
  assignAndUploadFile("diet_problem.json", json.dumps(diet_data, indent=2, ensure_ascii=False), 2, replace=True)
  dss.queueJob(finished_callback=finished, stdout_callback=getStdOut)  

placeholder = st.empty()
while (True):
  if job_completed:
    time.sleep(0.2)
  with placeholder.container():
    st.code(output)
  if job_completed:
    break
  time.sleep(0.05)

r = results.decode() if type(results) == bytes else results
final = json.loads(str(r))
results_df = st.table(pd.DataFrame(final["Diet"]))

latex_out = latex_out.decode() if type(latex_out) == bytes else latex_out
st.latex(latex_out)

if st.button('Do another run'):
  st.experimental_rerun()

    
