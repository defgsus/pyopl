#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <stdint.h>
#include <string.h>

#include "opl3.h"
#include "scheduler.h"

#ifndef DEFAULT_SAMPLE_RATE
#define DEFAULT_SAMPLE_RATE 49716
#endif

/* ------------------------------------------------------------------ */
/* Object definition                                                  */
/* ------------------------------------------------------------------ */


typedef struct {
    PyObject_HEAD
    opl3_chip chip;
    opl3_scheduler scheduler;
    long sample_rate;
} Opl3ChipObject;

static PyTypeObject Opl3ChipType;

/* ------------------------------------------------------------------ */
/* Helpers                                                            */
/* ------------------------------------------------------------------ */

static int
parse_register_and_value(
    PyObject *args, PyObject *kwargs, uint16_t *reg, uint8_t *value, uint64_t *sample
)
{
    long reg_long = 0;
    long value_long = 0;
    unsigned long long sample_long_long = 0;

    if (!sample) {
        static char *kwlist[] = {"reg", "value", NULL};
        if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|ll", kwlist, &reg_long, &value_long)) {
            return 0;
        }
    } else {
        static char *kwlist[] = {"reg", "value", "sample", NULL};
        if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|llK", kwlist, &reg_long, &value_long, &sample_long_long)) {
            return 0;
        }
    }

    if (reg_long < 0 || reg_long > 0xFFFF) {
        PyErr_Format(
            PyExc_ValueError,
            "register must be in range 0..65535, got %ld",
            reg_long
        );
        return 0;
    }

    if (value_long < 0 || value_long > 0xFF) {
        PyErr_Format(
            PyExc_ValueError,
            "value must be in range 0..255, got %ld",
            value_long
        );
        return 0;
    }

    *reg = (uint16_t)reg_long;
    *value = (uint8_t)value_long;
    if (sample) {
        *sample = (uint64_t)sample_long_long;
    }
    return 1;
}

static int check_samplerate(long sample_rate) {
    if (sample_rate <= 0 || sample_rate > 1000000) {
        PyErr_Format(
            PyExc_ValueError,
            "sample_rate must be in range 1..1000000, got %ld",
            sample_rate
        );
        return 1;
    }
    return 0;
}


/* ------------------------------------------------------------------ */
/* Constructor                                                        */
/* ------------------------------------------------------------------ */


static PyObject *
Opl3Chip_new(PyTypeObject *type, PyObject *args, PyObject *kwargs)
{
    (void)args;
    (void)kwargs;

    Opl3ChipObject *self;
    self = (Opl3ChipObject *)type->tp_alloc(type, 0);
    if (self == NULL) {
        return NULL;
    }

    memset(&self->chip, 0, sizeof(self->chip));
    memset(&self->scheduler, 0, sizeof(self->scheduler));

    return (PyObject *)self;
}

static int
Opl3Chip_init(Opl3ChipObject *self, PyObject *args, PyObject *kwargs)
{
    long sample_rate = DEFAULT_SAMPLE_RATE;
    uint8_t opl3_mode = 1;

    static char *kwlist[] = {"sample_rate", "opl3", NULL};
    if (!PyArg_ParseTupleAndKeywords(
            args, kwargs, "|lb:OPL3Chip", kwlist, &sample_rate, &opl3_mode)) {
        return -1;
    }

    if (check_samplerate(sample_rate) != 0) {
        return -1;
    }

    opl3_scheduler_init(&self->scheduler);

    OPL3_Reset(&self->chip, (uint32_t)sample_rate);
    if (opl3_mode) {
        OPL3_WriteReg(&self->chip, (uint16_t)0x105, (uint8_t)1);
    }
    self->sample_rate = sample_rate;

    return 0;
}

static void
Opl3Chip_dealloc(Opl3ChipObject *self)
{
    Py_TYPE(self)->tp_free((PyObject *)self);
}

/* ------------------------------------------------------------------ */
/* Methods                                                            */
/* ------------------------------------------------------------------ */

static PyObject *
Opl3Chip_reset(Opl3ChipObject *self, PyObject *args, PyObject *kwargs)
{
    long sample_rate = DEFAULT_SAMPLE_RATE;
    uint8_t opl3_mode = 1;

    static char *kwlist[] = {"sample_rate", "opl3", NULL};
    if (!PyArg_ParseTupleAndKeywords(
            args, kwargs, "|lb:OPL3Chip", kwlist, &sample_rate, &opl3_mode)) {
        return NULL;
    }

    if (check_samplerate(sample_rate) != 0) {
        return NULL;
    }

    OPL3_Reset(&self->chip, (uint32_t)sample_rate);
    if (opl3_mode) {
        OPL3_WriteReg(&self->chip, (uint16_t)0x105, (uint8_t)1);
    }
    self->sample_rate = sample_rate;
    // also clear scheduled writes
    opl3_scheduler_clear_schedule(&self->scheduler);

    Py_RETURN_NONE;
}

static PyObject *
Opl3Chip_write(Opl3ChipObject *self, PyObject *args, PyObject *kwargs)
{
    uint16_t reg;
    uint8_t value;
    uint64_t sample = 0;

    if (!parse_register_and_value(args, kwargs, &reg, &value, &sample)) {
        return NULL;
    }

    if (!sample) {
        OPL3_WriteReg(&self->chip, reg, value);
    } else {
        if (opl3_scheduler_schedule_write(
                &self->scheduler,
                sample,
                reg,
                value
            ) != 0)
        {
            PyErr_SetString(PyExc_OverflowError, "scheduler command queue is full");
            return NULL;
        }
    }

    Py_RETURN_NONE;
}

static PyObject *
Opl3Chip_delete_scheduled_writes(Opl3ChipObject *self)
{
    opl3_scheduler_clear_schedule(&self->scheduler);
    Py_RETURN_NONE;
}

static PyObject *
Opl3Chip_write_buffered(Opl3ChipObject *self, PyObject *args, PyObject *kwargs)
{
    uint16_t reg;
    uint8_t value;

    if (!parse_register_and_value(args, kwargs, &reg, &value, NULL)) {
        return NULL;
    }

    OPL3_WriteRegBuffered(&self->chip, reg, value);
    Py_RETURN_NONE;
}

/*
 * Render `frames` stereo frames into a newly allocated bytes object.
 *
 * The returned bytes contain interleaved little-endian int16 samples:
 *
 *     [left_0, right_0, left_1, right_1, ...]
 */
static PyObject *
Opl3Chip_generate_stream(Opl3ChipObject *self, PyObject *args)
{
    Py_ssize_t frames = 0;
    Py_ssize_t sample_count;
    PyObject *result;
    int16_t *output;
    uint32_t frame_count;

    if (!PyArg_ParseTuple(args, "n:generate_stream", &frames)) {
        return NULL;
    }

    if (frames < 0) {
        PyErr_SetString(PyExc_ValueError, "frames must be non-negative");
        return NULL;
    }

    if (frames > 0x7FFFFFFF) {
        PyErr_SetString(PyExc_ValueError, "frames is too large");
        return NULL;
    }

    sample_count = frames * 2;

    /* Guard against overflow in bytes: frames * 2 samples * 2 bytes. */
    if (frames > (PY_SSIZE_T_MAX / 4)) {
        PyErr_SetString(PyExc_OverflowError, "requested render size is too large");
        return NULL;
    }

    result = PyBytes_FromStringAndSize(NULL, sample_count * 2);
    if (result == NULL) {
        return NULL;
    }

    output = (int16_t *)PyBytes_AS_STRING(result);
    frame_count = (uint32_t)frames;

    Py_BEGIN_ALLOW_THREADS
    opl3_scheduler_render(&self->scheduler, &self->chip, output, frame_count, 0);
    //OPL3_GenerateStream(&self->chip, output, frame_count);
    Py_END_ALLOW_THREADS

    return result;
}

/*
 * Render directly into a writable Python buffer.
 *
 * Example:
 *
 *     buffer = bytearray(frames * 4)
 *     chip.generate_stream_into(frames, buffer)
 */
static PyObject *
Opl3Chip_generate_stream_into(Opl3ChipObject *self, PyObject *args, PyObject *kwargs)
{
    Py_ssize_t frames = 0;
    PyObject *buffer_object = NULL;
    uint8_t do_add = 0;
    Py_buffer view;
    int16_t *output;
    uint32_t frame_count;
    Py_ssize_t required_bytes;

    static char *kwlist[] = {"frames", "buffer", "do_add", NULL};

    if (!PyArg_ParseTupleAndKeywords(
            args, kwargs, "|nOb:generate_stream_into", kwlist, &frames, &buffer_object, &do_add)) {
        return NULL;
    }

    if (frames < 0) {
        PyErr_SetString(PyExc_ValueError, "frames must be non-negative");
        return NULL;
    }

    if (frames > 0x7FFFFFFF) {
        PyErr_SetString(PyExc_ValueError, "frames is too large");
        return NULL;
    }

    required_bytes = frames * 4;
    if (frames != 0 && required_bytes / frames != 4) {
        PyErr_SetString(PyExc_OverflowError, "requested render size is too large");
        return NULL;
    }

    if (PyObject_GetBuffer(
            buffer_object, &view, PyBUF_WRITABLE | PyBUF_C_CONTIGUOUS) != 0) {
        return NULL;
    }

    if (view.len < required_bytes) {
        PyBuffer_Release(&view);
        PyErr_Format(
            PyExc_ValueError,
            "buffer is too small: need at least %zd bytes for %zd stereo frames",
            required_bytes,
            frames
        );
        return NULL;
    }

    output = (int16_t *)view.buf;
    frame_count = (uint32_t)frames;

    Py_BEGIN_ALLOW_THREADS
    opl3_scheduler_render(&self->scheduler, &self->chip, output, frame_count, do_add);
    //OPL3_GenerateStream(&self->chip, output, frame_count);
    Py_END_ALLOW_THREADS

    PyBuffer_Release(&view);
    Py_RETURN_NONE;
}

/* ------------------------------------------------------------------ */
/* Getters                                                            */
/* ------------------------------------------------------------------ */

static PyObject *
Opl3Chip_get_sample_rate(PyObject *self, void *closure)
{
    return PyLong_FromUnsignedLongLong(((Opl3ChipObject*)self)->sample_rate);
}

static PyObject *
Opl3Chip_get_opl3(PyObject *self, void *closure)
{
    return PyBool_FromLong(((Opl3ChipObject*)self)->chip.newm != 0);
}

static PyObject *
Opl3Chip_get_current_sample(PyObject *self, void *closure)
{
    return PyLong_FromUnsignedLong(
        opl3_scheduler_current_sample_published(&((Opl3ChipObject*)self)->scheduler)
    );
}

/* ------------------------------------------------------------------ */
/* Getters                                                            */
/* ------------------------------------------------------------------ */

static PyGetSetDef Opl3Chip_getset[] = {
    {"sample_rate", Opl3Chip_get_sample_rate, NULL,
    "{{sample_rate}}", NULL},
    {"opl3", Opl3Chip_get_opl3, NULL,
    "{{opl3}}", NULL},
    {"current_sample", Opl3Chip_get_current_sample, NULL,
    "{{current_sample}}", NULL},
    {NULL}
};


/* ------------------------------------------------------------------ */
/* Method table                                                       */
/* ------------------------------------------------------------------ */

static PyMethodDef Opl3Chip_methods[] = {
    {
        "reset",
        (PyCFunction)Opl3Chip_reset,
        METH_VARARGS | METH_KEYWORDS,
        "{{reset}}"
    },
    {
        "write",
        (PyCFunction)Opl3Chip_write,
        METH_VARARGS | METH_KEYWORDS,
        "{{write}}"
    },
    {
        "write_buffered",
        (PyCFunction)Opl3Chip_write_buffered,
        METH_VARARGS | METH_KEYWORDS,
        "{{write_buffered}}"
    },
    {
        "delete_scheduled_writes",
        (PyCFunction)Opl3Chip_delete_scheduled_writes,
        METH_NOARGS,
        "{{delete_scheduled_writes}}"
    },
    {
        "generate_stream",
        (PyCFunction)Opl3Chip_generate_stream,
        METH_VARARGS,
        "{{generate_stream}}"
    },
    {
        "generate_stream_into",
        (PyCFunction)Opl3Chip_generate_stream_into,
        METH_VARARGS | METH_KEYWORDS,
        "{{generate_stream_into}}"
    },
    {NULL, NULL, 0, NULL}
};

/* ------------------------------------------------------------------ */
/* Type definition                                                     */
/* ------------------------------------------------------------------ */

static PyTypeObject Opl3ChipType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "pyopl.OPL3Chip",
    .tp_basicsize = sizeof(Opl3ChipObject),
    .tp_itemsize = 0,
    .tp_dealloc = (destructor)Opl3Chip_dealloc,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_doc = "{{class}}",
    .tp_methods = Opl3Chip_methods,
    .tp_init = (initproc)Opl3Chip_init,
    .tp_new = Opl3Chip_new,
    .tp_getset = Opl3Chip_getset,
};

/* ------------------------------------------------------------------ */
/* Module definition                                                   */
/* ------------------------------------------------------------------ */

static PyModuleDef opl3_module = {
    PyModuleDef_HEAD_INIT,
    "pyopl._opl3",
    "Low-level bindings for the Nuked-OPL3 emulator.",
    -1,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL
};

PyMODINIT_FUNC
PyInit__opl3(void)
{
    PyObject *module;

    if (PyType_Ready(&Opl3ChipType) < 0) {
        return NULL;
    }

    module = PyModule_Create(&opl3_module);
    if (module == NULL) {
        return NULL;
    }

    Py_INCREF(&Opl3ChipType);
    if (PyModule_AddObject(module, "OPL3Chip", (PyObject *)&Opl3ChipType) < 0) {
        Py_DECREF(&Opl3ChipType);
        Py_DECREF(module);
        return NULL;
    }

    return module;
}
