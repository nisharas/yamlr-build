import pytest
import yamlr_native
from ruamel.yaml import YAML
import yaml as pyyaml

def test_native_vs_ruamel_parity():
    content = """
kind: Pod
apiVersion: v1
metadata:
  name: test-pod
  labels:
    app: test
spec:
  containers:
  - name: nginx
    image: nginx:latest
    ports:
    - containerPort: 80
"""
    # Native
    native_docs = yamlr_native.native_parse_to_dict(content)
    
    # Ruamel
    ryaml = YAML(typ='safe')
    ruamel_docs = list(ryaml.load_all(content))
    
    # Convert ruamel objects to plain dicts for comparison if needed
    # (ruamel.yaml.comments.CommentedMap inherits from dict usually)
    
    assert len(native_docs) == len(ruamel_docs)
    assert native_docs[0] == ruamel_docs[0]

def test_multi_document_parity():
    content = """
kind: Service
apiVersion: v1
metadata:
  name: svc-1
---
kind: Service
apiVersion: v1
metadata:
  name: svc-2
"""
    native_docs = yamlr_native.native_parse_to_dict(content)
    
    ryaml = YAML(typ='safe')
    ruamel_docs = list(ryaml.load_all(content))
    
    assert len(native_docs) == 2
    assert native_docs[0]['metadata']['name'] == 'svc-1'
    assert native_docs[1]['metadata']['name'] == 'svc-2'
    assert native_docs == ruamel_docs

def test_complex_types_parity():
    content = """
boolean: true
integer: 123
float: 123.456
string: "hello"
null_val: null
list:
  - 1
  - 2
  - 3
dict:
  key: value
"""
    native_docs = yamlr_native.native_parse_to_dict(content)
    
    ryaml = YAML(typ='safe')
    ruamel_docs = list(ryaml.load_all(content))
    
    assert native_docs == ruamel_docs
