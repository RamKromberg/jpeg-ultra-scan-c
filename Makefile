CC = gcc
# Base production flags optimized for performance
CFLAGS = -O3 -std=c11 $(shell pkg-config --cflags libjpeg)
LIBS = $(shell pkg-config --libs libjpeg)

TARGET = jpeg-ultra-scan-c
SRC = main.c utils.c
HEADERS = utils.h channel.h
OBJ = $(SRC:.c=.o)

# Debug specific variables
DEBUG_TARGET = $(TARGET)_debug
DEBUG_CFLAGS = $(CFLAGS) -Wall -Wextra -DDIAGNOSTIC_TRACE
DEBUG_OBJ = $(SRC:.c=.debug.o)

# Default target (Release)
all: $(TARGET)

# Release Build rule
$(TARGET): $(OBJ)
	$(CC) $(CFLAGS) -o $(TARGET) $(OBJ) $(LIBS)

%.o: %.c $(HEADERS)
	$(CC) $(CFLAGS) -c $< -o $@

# Debug Target Rule
debug: $(DEBUG_TARGET)

# Debug Build rule
$(DEBUG_TARGET): $(DEBUG_OBJ)
	$(CC) $(DEBUG_CFLAGS) -o $(DEBUG_TARGET) $(DEBUG_OBJ) $(LIBS)

%.debug.o: %.c $(HEADERS)
	$(CC) $(DEBUG_CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJ) $(DEBUG_OBJ) $(TARGET) $(DEBUG_TARGET)
	rm -rf .cache_c_outputs

format:
	clang-format -i *.c *.h

test: all
	python3 test_harness.py

bench: debug
	python3 test_harness.py --bench --binary ./$(DEBUG_TARGET)

comp: debug
	./pipeline_comparator.sh

.PHONY: all debug clean format test bench comp
