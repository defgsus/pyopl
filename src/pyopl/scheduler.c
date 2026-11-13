#include "scheduler.h"

#include <string.h>

/* ------------------------------------------------------------------ */
/* SPSC command ring                                                   */
/* ------------------------------------------------------------------ */

static int
command_ring_push(
    opl3_command_ring *ring,
    uint64_t sample,
    uint16_t reg,
    uint8_t value
)
{
    size_t tail = atomic_load_explicit(&ring->tail, memory_order_relaxed);
    size_t head = atomic_load_explicit(&ring->head, memory_order_acquire);
    size_t next_tail = (tail + 1) % OPL3_SCHEDULER_COMMAND_CAPACITY;

    if (next_tail == head) {
        return -1; /* Full */
    }

    ring->items[tail].sample = sample;
    ring->items[tail].reg = reg;
    ring->items[tail].value = value;

    atomic_store_explicit(&ring->tail, next_tail, memory_order_release);
    return 0;
}

static int
command_ring_pop(opl3_command_ring *ring, opl3_scheduled_event *event)
{
    size_t head = atomic_load_explicit(&ring->head, memory_order_relaxed);
    size_t tail = atomic_load_explicit(&ring->tail, memory_order_acquire);

    if (head == tail) {
        return 0; /* Empty */
    }

    *event = ring->items[head];
    atomic_store_explicit(
        &ring->head,
        (head + 1) % OPL3_SCHEDULER_COMMAND_CAPACITY,
        memory_order_release
    );

    return 1;
}

/* ------------------------------------------------------------------ */
/* Event min-heap                                                      */
/* ------------------------------------------------------------------ */

static int
event_less(
    const opl3_scheduled_event *a,
    const opl3_scheduled_event *b
)
{
    if (a->sample != b->sample) {
        return a->sample < b->sample;
    }

    /* Stable enough ordering for multiple writes at one sample. */
    if (a->reg != b->reg) {
        return a->reg < b->reg;
    }

    return a->value < b->value;
}

static void
event_heap_swap(
    opl3_scheduled_event *a,
    opl3_scheduled_event *b
)
{
    opl3_scheduled_event temporary = *a;
    *a = *b;
    *b = temporary;
}

static void
event_heap_push(
    opl3_scheduler *scheduler,
    const opl3_scheduled_event *event
)
{
    size_t child;
    size_t parent;

    if (scheduler->event_count >= OPL3_SCHEDULER_EVENT_CAPACITY) {
        return;
    }

    child = scheduler->event_count++;
    scheduler->events[child] = *event;

    while (child > 0) {
        parent = (child - 1) / 2;

        if (!event_less(&scheduler->events[child], &scheduler->events[parent])) {
            break;
        }

        event_heap_swap(
            &scheduler->events[child],
            &scheduler->events[parent]
        );
        child = parent;
    }
}

static int
event_heap_peek(
    const opl3_scheduler *scheduler,
    uint64_t *sample
)
{
    if (scheduler->event_count == 0) {
        return 0;
    }

    *sample = scheduler->events[0].sample;
    return 1;
}

static void
event_heap_pop(opl3_scheduler *scheduler)
{
    size_t parent = 0;
    size_t child;

    if (scheduler->event_count == 0) {
        return;
    }

    scheduler->events[0] = scheduler->events[--scheduler->event_count];

    for (;;) {
        size_t left = parent * 2 + 1;
        size_t right = parent * 2 + 2;
        size_t smallest = parent;

        if (left < scheduler->event_count &&
            event_less(&scheduler->events[left], &scheduler->events[smallest])) {
            smallest = left;
        }

        if (right < scheduler->event_count &&
            event_less(&scheduler->events[right], &scheduler->events[smallest])) {
            smallest = right;
        }

        if (smallest == parent) {
            break;
        }

        event_heap_swap(
            &scheduler->events[parent],
            &scheduler->events[smallest]
        );
        parent = smallest;
    }

    (void)child;
}

/* ------------------------------------------------------------------ */
/* Scheduler lifecycle                                                 */
/* ------------------------------------------------------------------ */

void opl3_scheduler_init(opl3_scheduler *scheduler)
{
    memset(scheduler, 0, sizeof(*scheduler));

    atomic_init(&scheduler->commands.head, 0);
    atomic_init(&scheduler->commands.tail, 0);

    scheduler->sample_position = 0;
    atomic_init(&scheduler->sample_position_published, 0);
}

void
opl3_scheduler_deinit(opl3_scheduler *scheduler)
{
    /* The scheduler owns no heap-allocated memory. */
    (void)scheduler;
}

int
opl3_scheduler_schedule_write(
    opl3_scheduler *scheduler,
    uint64_t sample_position,
    uint16_t reg,
    uint8_t value
)
{
    if (scheduler == NULL) {
        return -1;
    }

    return command_ring_push(
        &scheduler->commands,
        sample_position,
        reg,
        value
    );
}

uint64_t
opl3_scheduler_current_sample(const opl3_scheduler *scheduler)
{
    return scheduler->sample_position;
}

uint64_t
opl3_scheduler_current_sample_published(const opl3_scheduler *scheduler)
{
    return atomic_load_explicit(
        &scheduler->sample_position_published,
        memory_order_acquire
    );
}

void
opl3_scheduler_clear_schedule(opl3_scheduler *scheduler)
{
    command_ring_push(
        &scheduler->commands,
        0,                       /* Sample is irrelevant for a clear. */
        OPL3_SCHEDULER_CLEAR_REG,
        0
    );
}

/* ------------------------------------------------------------------ */
/* Rendering                                                           */
/* ------------------------------------------------------------------ */

static void
drain_commands(opl3_scheduler *scheduler)
{
    opl3_scheduled_event command;

    while (command_ring_pop(&scheduler->commands, &command)) {
        if (command.reg == OPL3_SCHEDULER_CLEAR_REG) {
            scheduler->event_count = 0;
            continue;
        }

        event_heap_push(scheduler, &command);
    }
}

static void
apply_due_events(opl3_scheduler *scheduler, opl3_chip *chip)
{
    while (scheduler->event_count > 0 &&
           scheduler->events[0].sample <= scheduler->sample_position) {
        opl3_scheduled_event event = scheduler->events[0];

        event_heap_pop(scheduler);

        OPL3_WriteReg(
            chip,
            event.reg,
            event.value
        );
    }
}

static int16_t OPL3_ClipSample(int32_t sample)
{
    if (sample > 32767)
    {
        sample = 32767;
    }
    else if (sample < -32768)
    {
        sample = -32768;
    }
    return (int16_t)sample;
}

void OPL3_GenerateStreamAdd(opl3_chip *chip, int16_t *sndptr, uint32_t numsamples)
{
    int16_t samples[4];
    uint_fast32_t i;

    for(i = 0; i < numsamples; i++)
    {
        OPL3_Generate4ChResampled(chip, samples);
        sndptr[0] = OPL3_ClipSample((uint32_t)sndptr[0] + (uint32_t)samples[0]);
        sndptr[1] = OPL3_ClipSample((uint32_t)sndptr[1] + (uint32_t)samples[1]);
        sndptr += 2;
    }
}

void
opl3_scheduler_render(
    opl3_scheduler *scheduler,
    opl3_chip *chip,
    int16_t *output,
    uint32_t frames,
    uint8_t do_add
)
{
    uint32_t rendered = 0;

    while (rendered < frames) {
        uint64_t block_start;
        uint64_t block_end;
        uint64_t next_event_sample;
        uint32_t run;
        int has_next_event;

        drain_commands(scheduler);

        /* Apply events scheduled at or before the current render position.
           This includes events that arrived late because of control-thread
           or audio-device latency. */
        apply_due_events(scheduler, chip);

        block_start = scheduler->sample_position;
        block_end = block_start + (frames - rendered);

        has_next_event = event_heap_peek(
            scheduler,
            &next_event_sample
        );

        if (has_next_event && next_event_sample < block_end) {
            run = (uint32_t)(next_event_sample - block_start);
        } else {
            run = frames - rendered;
        }

        if (run == 0) {
            /* Multiple events share this exact sample position. */
            apply_due_events(scheduler, chip);
            continue;
        }

        if (do_add) {
            OPL3_GenerateStreamAdd(chip, output + (rendered * 2), run);
        } else {
            OPL3_GenerateStream(chip, output + (rendered * 2), run);
        }

        scheduler->sample_position += run;
        rendered += run;

        atomic_store_explicit(
            &scheduler->sample_position_published,
            scheduler->sample_position,
            memory_order_release
        );
    }
}
