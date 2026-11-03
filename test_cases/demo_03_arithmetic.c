/*
 * Test 3: Division and modulo by zero.
 */

int divide_by_zero(int numerator)
{
    int divisor = 0;

    return numerator / divisor;
}

int modulo_by_zero(void)
{
    int divisor = 0;

    return 100 % divisor;
}

int safe_division(int numerator, int denominator)
{
    if (denominator == 0)
    {
        return 0;
    }

    return numerator / denominator;
}
