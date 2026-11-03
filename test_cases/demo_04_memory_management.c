/*
 * Test 4: Memory leaks, use-after-free and double-free.
 */

#include <stdlib.h>

int memory_leak_example(void)
{
    int *buffer = malloc(4 * sizeof(*buffer));

    if (buffer == NULL)
    {
        return -1;
    }

    buffer[0] = 42;

    /* Allocated memory is never released. */
    return buffer[0];
}

int use_after_free_example(void)
{
    int *buffer = malloc(sizeof(*buffer));

    if (buffer == NULL)
    {
        return -1;
    }

    *buffer = 50;

    free(buffer);

    /* Accessing memory after it has been freed. */
    return *buffer;
}

int double_free_example(void)
{
    int *buffer = malloc(sizeof(*buffer));

    if (buffer == NULL)
    {
        return -1;
    }

    free(buffer);

    /* Releasing the same memory a second time. */
    free(buffer);

    return 0;
}
