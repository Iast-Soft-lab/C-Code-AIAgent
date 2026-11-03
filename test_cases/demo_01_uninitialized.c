/*
 * Test 1: Uninitialized variable detection.
 */

int return_uninitialized_value(void)
{
    int value;

    return value;
}

int branch_on_uninitialized_value(void)
{
    int status;

    if (status > 0)
    {
        return 1;
    }

    return 0;
}
