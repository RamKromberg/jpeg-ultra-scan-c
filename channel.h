#ifndef CHANNEL_H
#define CHANNEL_H

#include <stdbool.h>
#include <stdlib.h>
#include <threads.h>

// Represents a standalone progressive scan script definition
typedef struct {
	jpeg_scan_info scans[64]; /* Passed by value on the queue stack line */
	int num_scans;
	int scan_id;
} scan_config_t;

typedef struct {
	scan_config_t* buffer;
	size_t capacity;
	size_t head;
	size_t tail;
	size_t size;
	bool closed;
	mtx_t mutex;
	cnd_t not_full;
	cnd_t not_empty;
} csp_channel_t;

static inline csp_channel_t* channel_create(size_t capacity) {
	csp_channel_t* chan = malloc(sizeof(csp_channel_t));
	if (!chan)
		return NULL;
	chan->buffer = malloc(capacity * sizeof(scan_config_t));
	if (!chan->buffer) {
		free(chan);
		return NULL;
	}
	chan->capacity = capacity;
	chan->head = 0;
	chan->tail = 0;
	chan->size = 0;
	chan->closed = false;

	if (mtx_init(&chan->mutex, mtx_plain) != thrd_success)
		return NULL;
	if (cnd_init(&chan->not_full) != thrd_success)
		return NULL;
	if (cnd_init(&chan->not_empty) != thrd_success)
		return NULL;

	return chan;
}

static inline bool channel_send(csp_channel_t* chan, scan_config_t item) {
	mtx_lock(&chan->mutex);
	while (chan->size == chan->capacity && !chan->closed) {
		cnd_wait(&chan->not_full, &chan->mutex);
	}
	if (chan->closed) {
		mtx_unlock(&chan->mutex);
		return false;
	}
	chan->buffer[chan->tail] = item;
	chan->tail = (chan->tail + 1) % chan->capacity;
	chan->size++;

	cnd_signal(&chan->not_empty);
	mtx_unlock(&chan->mutex);
	return true;
}

static inline bool channel_receive(csp_channel_t* chan, scan_config_t* item) {
	mtx_lock(&chan->mutex);
	while (chan->size == 0 && !chan->closed) {
		cnd_wait(&chan->not_empty, &chan->mutex);
	}
	if (chan->size == 0 && chan->closed) {
		mtx_unlock(&chan->mutex);
		return false;
	}
	*item = chan->buffer[chan->head];
	chan->head = (chan->head + 1) % chan->capacity;
	chan->size--;

	cnd_signal(&chan->not_full);
	mtx_unlock(&chan->mutex);
	return true;
}

static inline void channel_close(csp_channel_t* chan) {
	mtx_lock(&chan->mutex);
	chan->closed = true;
	cnd_broadcast(&chan->not_empty);
	cnd_broadcast(&chan->not_full);
	mtx_unlock(&chan->mutex);
}

static inline void channel_destroy(csp_channel_t* chan) {
	if (!chan)
		return;
	free(chan->buffer);
	mtx_destroy(&chan->mutex);
	cnd_destroy(&chan->not_full);
	cnd_destroy(&chan->not_empty);
	free(chan);
}

#endif // CHANNEL_H
