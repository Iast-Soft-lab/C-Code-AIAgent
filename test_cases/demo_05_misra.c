/*
 * Test 5: Selected MISRA C:2012 and code-quality checks.
 */

#include <stdio.h>

/* External function definitions without prior prototypes. */
int calculate_total(int input)
{
    return input + 10;
}

/* Unused function parameter. */
int get_fixed_value(int unused_parameter)
{
    return 100;
}

/* Ignoring a non-void function's return value. */
void ignore_return_value(void)
{
    calculate_total(5);
}

/* Standard I/O library use and ignored return value. */
void use_standard_io(void)
{
    printf("Static analysis demonstration\n");
}
