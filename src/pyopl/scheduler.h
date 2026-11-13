#ifndef PYOPL3_SCHEDULER_H
#define PYOPL3_SCHEDULER_H

#include <stdint.h>
#include <stddef.h>
#include <stdatomic.h>

#include "opl3.h"

#define OPL3_SCHEDULER_EVENT_CAPACITY 16384
#define OPL3_SCHEDULER_COMMAND_CAPACITY 16384
#define OPL3_SCHEDULER_CLEAR_REG 0xFFFFu

typedef struct {
    uint64_t sample;
    uint16_t reg;
    uint8_t value;
} opl3_scheduled_event;

/* Single-producer / single-consumer command ring.
 *
 * Python/control thread: producer.
 * Audio callback thread: consumer.
 */
typedef struct {
    _Atomic size_t head;
    _Atomic size_t tail;
    opl3_scheduled_event items[OPL3_SCHEDULER_COMMAND_CAPACITY];
} opl3_command_ring;

typedef struct {
    /* Number of stereo frames already rendered since reset, owned by audio thread */
    uint64_t sample_position;

    /* Min-heap of pending events, owned by the audio thread. */
    opl3_scheduled_event events[OPL3_SCHEDULER_EVENT_CAPACITY];
    size_t event_count;

    opl3_command_ring commands;

    /* Atomic position published for control threads.
       Updated by the audio thread, read by Python. */
    _Atomic uint64_t sample_position_published;

} opl3_scheduler;

void opl3_scheduler_init(opl3_scheduler *scheduler);
void opl3_scheduler_deinit(opl3_scheduler *scheduler);

/*
 * Thread-safe.
 *
 * Returns 0 on success, -1 if the command ring is full.
 */
int opl3_scheduler_schedule_write(
    opl3_scheduler *scheduler,
    uint64_t sample_position,
    uint16_t reg,
    uint8_t value
);

/* Thread-safe. Current sample position, published by audio-thread */
uint64_t opl3_scheduler_current_sample_published(const opl3_scheduler *scheduler);

/*
 * Thread-safe.
 *
 * Requests removal of every currently scheduled event. The clear takes
 * effect on the audio thread in command order: events scheduled before
 * this call are discarded; events scheduled after it remain.
 */
void opl3_scheduler_clear_schedule(opl3_scheduler *scheduler);

/* Audio-thread only. */
uint64_t opl3_scheduler_current_sample(const opl3_scheduler *scheduler);

/*
 * Audio-thread only.
 *
 * Renders exactly `frames` stereo frames into `output`.
 * `output` must have room for frames * 2 int16 samples.
 */
void opl3_scheduler_render(
    opl3_scheduler *scheduler,
    opl3_chip *chip,
    int16_t *output,
    uint32_t frames,
    uint8_t do_add
);

#endif
