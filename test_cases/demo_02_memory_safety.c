/*
 * Test 2: Array bounds and null pointer detection.
 */

int read_out_of_bounds(void)
{
    int values[3] = {10, 20, 30};

    return values[3];
}

int read_through_null_pointer(void)
{
    int *pointer = 0;

    return *pointer;
}

int write_through_null_pointer(void)
{
    int *pointer = 0;

    *pointer = 100;

    return 0;
}
