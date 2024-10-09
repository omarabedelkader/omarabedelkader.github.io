---
title: ''
date: 2024-09-12
permalink: /posts/2024/09/blog-post-4/
tags:
  - Pharo
  - Smalltalk
  - Beginner
---

# Pharo Exercises:

## Basics 
### Exercise 1:
Write a Pharo script to print 'Hello World ' on screen and your name on a separate line.

<em>

Expected Output :

Hello World

Alexandra Abramov

</em>

Solution:
```
Transcript show: 'Hello World';cr.
Transcript show: 'John Doe';cr.
```

### Exercise 2:
Write a Pharo Script to print the sum of two numbers.
<em>

Test Data:
74 + 36

Expected Output :
110

</em>

Solution:
```
| num1 num2 sum |
num1 := 74.
num2 := 36.
sum := num1 + num2.
Transcript show: 'The sum of ', num1 printString, ' and ', num2 printString, ' is: ', sum printString; cr.

```

#### To be able to get a input from the user:

```
| num1 num2 sum |
num1 := (UIManager default request: 'Enter the first number') asNumber.
num2 := (UIManager default request: 'Enter the second number') asNumber.
sum := num1 + num2.
Transcript show: 'The sum of ', num1 printString, ' and ', num2 printString, ' is: ', sum printString; cr.

```

### Exercise 3 : 
Write a Pharo script to divide two numbers and print them on the screen. 
<em>

Test Data:
74 + 36

Expected Output :
110

</em>

Solution :
```
| num1 num2 sum |
num1 := 74.
num2 := 36.
sum := num1 / num2.
Transcript show: 'The sum of ', num1 printString, ' and ', num2 printString, ' is: ', sum printString; cr.

```

#### To be able to show the decimal valuees (the first two)

```
| num1 num2 result |
num1 := 74.
num2 := 36.
result := num1 / num2.
Transcript show: 'The division of ', num1 printString, ' by ', num2 printString, ' is: ', (result printShowingDecimalPlaces: 2); cr.

```

#### More robust code to with if and else to protect the code from the error of dividing from 0:

```
| num1 num2 result |
num1 := (UIManager default request: 'Enter the first number') asNumber.
num2 := (UIManager default request: 'Enter the second number') asNumber.
(num2 = 0)
    ifTrue: [ 
        Transcript show: 'Error: Division by zero is not allowed!'; cr. 
    ]
    ifFalse: [
        result := num1 / num2.
        Transcript show: 'The division of ', num1 printString, ' by ', num2 printString, ' is: ', result printString; cr.
    ].

```

### Exercise 4;
Write a Pharo script to print the results of the following operations.

<em>
Test Data:

a. -5 + 8 * 6

b. (55+9) % 9

c. 20 + -3*5 / 8

d. 5 + 15 / 3 * 2 - 8 % 3

Expected Output :

43

1

19

13

</em>

Solution :

```
Transcript show: 'Result of a (-5 + 8 * 6): ', (-5 + 8 * 6) printString; cr.
Transcript show: 'Result of b ((55 + 9) % 9): ', ((55 + 9) \\ 9) printString; cr.
Transcript show: 'Result of c (20 + -3 * 5 / 8): ', (20 + (-3 * 5) / 8) printString; cr.
Transcript show: 'Result of d (5 + 15 / 3 * 2 - 8 % 3): ', (5 + (15 / 3 * 2) - 8 \\ 3) printString; cr.

```

### Exercise 5:

Write a Pharo script that takes a number as input and prints its multiplication table up to 10.

<em>
Test Data:

Input a number: 8

Expected Output :

8 x 1 = 8

8 x 2 = 16

8 x 3 = 24

...

8 x 10 = 80

</em>

Solution:

```
| number |
number := UIManager default request: 'Input a number:'.
number := number asInteger.

1 to: 10 do: [:i |
    Transcript show: number printString, ' x ', i printString, ' = ', (number * i) printString; cr.
].

```
#### Improving my code:

```
| number table |
number := UIManager default request: 'Input a Number:'.
table := UIManager default request: 'Input the second Number'.

number := number asInteger.
table := table asInteger.
1 to: table do: [:i | Transcript show: number printString, 'x', i printString, '=', (number *i) printString;cr.].
```


### Exercise 6:
Write a Java program to print the area and perimeter of a circle.

<em>
Test Data:

Radius = 7.5

Expected Output

Perimeter is = 47.12388980384689

Area is = 176.71458676442586 

</em>

Solution:

```
| radius perimeter area pi |
radius := 7.5.
pi := Float pi.

perimeter := 2 * pi * radius.

area := pi * radius * radius.

Transcript show: 'Perimeter is = ', perimeter asString; cr.
Transcript show: 'Area is = ', area asString; cr.

```

### Exercise 7:
Write a Pharo script to print an American flag on the screen.
```
Expected Output

* * * * * * ==================================                          
 * * * * *  ==================================                          
* * * * * * ==================================                          
 * * * * *  ==================================                          
* * * * * * ==================================                          
 * * * * *  ==================================                          
* * * * * * ==================================                          
 * * * * *  ==================================                          
* * * * * * ==================================                          
==============================================                          
==============================================                          
==============================================                          
==============================================                          
==============================================                          
==============================================
```


Solution:

```
 1 to: 9 do: [:i |
            (i odd)
                ifTrue: [Transcript show: '* * * * * * ================================== '; cr]
                ifFalse: [Transcript show: ' * * * * *  ================================== '; cr].
        ].
        1 to: 6 do: [:i |
            Transcript show: '=============================================='; cr.
        ].
```

### Exercise 8: 
Write a Pharo script to swap two variables. 


Solution:

```
| a b temp |

a := 10.
b := 20.

Transcript show: 'Before swap: a = ', a printString, ', b = ', b printString; cr.

"Swapping the values"
temp := a.
a := b.
b := temp.

Transcript show: 'After swap: a = ', a printString, ', b = ', b printString; cr.

```

## Exercise 9: Write a Pharo program to multiply two binary numbers. 

Input Data:
Input the first binary number: 10
Input the second binary number: 11
Expected Output

Product of two binary numbers: 110 


Solution:

```
| binary1 binary2 product decimal1 decimal2 |

"Input binary numbers as strings"
binary1 := '10'.
binary2 := '11'.

"Convert binary strings to decimal integers"
decimal1 := Integer readFrom: binary1 radix: 2.
decimal2 := Integer readFrom: binary2 radix: 2.

"Multiply the decimal integers"
product := decimal1 * decimal2.

"Convert the product back to binary"
Transcript show: 'Product of two binary numbers: ', (product printStringBase: 2); cr.

```


##  Exercise 10:  

Write a Pharo program to convert an integer number to a binary number.

Input Data:
Input a Decimal Number : 5
Expected Output

Binary number is: 101 

Solution:

```
| decimalNumber binaryNumber |

"Input a decimal number"
decimalNumber := 5.

"Convert the decimal number to binary"
binaryNumber := decimalNumber printStringBase: 2.

"Display the result"
Transcript show: 'Binary number is: ', binaryNumber; cr.

```

## Exercise 11:
Write a Pharo program to compare two numbers.
Input Data:
Input first integer: 25
Input second integer: 39
Expected Output

25 != 39                                                                          
25 < 39                                                                           
25 <= 39



Solution:

```
| num1 num2 |

"Input numbers"
num1 := 3.
num2 := 39.

"Performing comparisons and printing the results"
(num1 = num2) ifTrue: [ Transcript show: num1 printString, ' = ', num2 printString; cr. ].
(num1 ~= num2) ifTrue: [ Transcript show: num1 printString, ' != ', num2 printString; cr. ].
(num1 < num2) ifTrue: [ Transcript show: num1 printString, ' < ', num2 printString; cr. ].
(num1 <= num2) ifTrue: [ Transcript show: num1 printString, ' <= ', num2 printString; cr. ].

```