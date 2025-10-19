// cSigner.c
// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025 Moew72 <Moew72@proton.me>
// Copyright (C) 2025 Harcic <harcic@outlook.com>

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <link.h>

#ifndef __USE_GNU
#define __USE_GNU
#endif

static char** libs = NULL;
static uintptr_t offset = 0;
static uintptr_t module_base = 0;
static void* module = NULL;
static void* sign_func = NULL;

static int callback(struct dl_phdr_info* info, size_t size, void* data) {
    if (info->dlpi_name && strstr(info->dlpi_name, "wrapper.node")) {
        module_base = info->dlpi_addr;
        return 1;
    }
    return 0;
}

static PyObject* py_load_module(PyObject* self, PyObject* args) {
    for (int i = 0; libs[i] != NULL; i++) {
        void* handle = dlopen(libs[i], RTLD_LAZY | RTLD_GLOBAL);
        if (!handle) {
            PyErr_SetString(PyExc_RuntimeError, dlerror());
            return NULL;
        }
    }

    module = dlopen("./wrapper.node", RTLD_LAZY);
    if (!module) {
        PyErr_SetString(PyExc_RuntimeError, dlerror());
        return NULL;
    }

    dl_iterate_phdr(callback, NULL);
    if (module_base == 0) {
        dlclose(module);
        PyErr_SetString(PyExc_RuntimeError, "Failed to find module base");
        return NULL;
    }

    sign_func = (void*)(module_base + offset);
    if ((uintptr_t)sign_func < 0x1000) {
        dlclose(module);
        PyErr_SetString(PyExc_RuntimeError, "Invalid function pointer");
        return NULL;
    }

    Py_RETURN_NONE;
}

static PyObject* py_unload_module(PyObject* self, PyObject* args) {
    if (module) {
        dlclose(module);
        module = NULL;
        sign_func = NULL;
        module_base = 0;
    }
    Py_RETURN_NONE;
}

static PyObject* py_set_libs(PyObject* self, PyObject* args) {
    PyObject* libs_list;
    if (!PyArg_ParseTuple(args, "O", &libs_list)) {
        return NULL;
    }

    if (!PyList_Check(libs_list)) {
        PyErr_SetString(PyExc_TypeError, "Expected a list");
        return NULL;
    }

    Py_ssize_t num_libs = PyList_Size(libs_list);

    libs = (char**)malloc((num_libs + 1) * sizeof(char*));
    if (!libs) {
        PyErr_SetString(PyExc_MemoryError, "Failed to allocate memory for libs");
        return NULL;
    }

    for (Py_ssize_t i = 0; i < num_libs; i++) {
        PyObject* lib_str = PyList_GetItem(libs_list, i);
        if (!PyUnicode_Check(lib_str)) {
            free(libs);
            PyErr_SetString(PyExc_TypeError, "Expected string in list");
            return NULL;
        }

        const char* lib_cstr = PyUnicode_AsUTF8(lib_str);
        libs[i] = strdup(lib_cstr);
        if (!libs[i]) {
            // 清理已分配的内存
            for (Py_ssize_t j = 0; j < i; j++) {
                free(libs[j]);
            }
            free(libs);
            PyErr_SetString(PyExc_MemoryError, "Failed to duplicate string");
            return NULL;
        }
    }
    libs[num_libs] = NULL;

    Py_RETURN_NONE;
}

static PyObject* py_set_offset(PyObject* self, PyObject* args) {
    unsigned long long offset_val;
    if (!PyArg_ParseTuple(args, "K", &offset_val)) {
        return NULL;
    }

    offset = (uintptr_t)offset_val;
    Py_RETURN_NONE;
}

static PyObject* py_sign(PyObject* self, PyObject* args) {
    const char* cmd;
    const char* src_data;
    Py_ssize_t src_len;
    int seq;

    if (!PyArg_ParseTuple(args, "sy#i", &cmd, &src_data, &src_len, &seq)) {
        return NULL;
    }

    if (!sign_func) {
        PyErr_SetString(PyExc_RuntimeError, "Sign function not loaded");
        return NULL;
    }

    unsigned char output_buf[0x300] = {0};

    typedef int (*sign_func_t)(const char*, const unsigned char*, int, int, unsigned char*);
    sign_func_t func = (sign_func_t)sign_func;

    int result = func(cmd, (const unsigned char*)src_data, (int)src_len, seq, output_buf);

    if (result != 0) {
        PyErr_SetString(PyExc_RuntimeError, "Sign function returned error");
        return NULL;
    }

    unsigned char token_len = output_buf[0x0FF];
    unsigned char extra_len = output_buf[0x1FF];
    unsigned char sign_len = output_buf[0x2FF];

    PyObject* token_bytes = PyBytes_FromStringAndSize((const char*)output_buf, token_len);
    PyObject* extra_bytes = PyBytes_FromStringAndSize((const char*)output_buf + 0x100, extra_len);
    PyObject* sign_bytes = PyBytes_FromStringAndSize((const char*)output_buf + 0x200, sign_len);

    if (!token_bytes || !extra_bytes || !sign_bytes) {
        Py_XDECREF(token_bytes);
        Py_XDECREF(extra_bytes);
        Py_XDECREF(sign_bytes);
        return NULL;
    }

    PyObject* result_tuple = PyTuple_New(3);
    PyTuple_SetItem(result_tuple, 0, token_bytes);
    PyTuple_SetItem(result_tuple, 1, extra_bytes);
    PyTuple_SetItem(result_tuple, 2, sign_bytes);

    return result_tuple;
}

static PyMethodDef SignExtensionMethods[] = {
    {"load_module", py_load_module, METH_NOARGS, "Load the sign module"},
    {"unload_module", py_unload_module, METH_NOARGS, "Unload the sign module"},
    {"set_libs", py_set_libs, METH_VARARGS, "Set library list"},
    {"set_offset", py_set_offset, METH_VARARGS, "Set function offset"},
    {"sign", py_sign, METH_VARARGS, "Perform signing"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef signmodule = {
    PyModuleDef_HEAD_INIT,
    "cSigner",
    "Sign extension module for calling wrapper.node functions by offset",
    -1,
    SignExtensionMethods
};

PyMODINIT_FUNC PyInit_cSigner(void) {
    return PyModule_Create(&signmodule);
}