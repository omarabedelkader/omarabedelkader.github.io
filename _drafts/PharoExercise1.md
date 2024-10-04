---
title: ''
date: 2024-09-12
permalink: /posts/2024/09/blog-post-4/
tags:
  - Pharo
  - Smalltalk
  - Beginner
---



# Exercises: Simple Counter in Pharr

## Exercise 1: First we need to create a package called MyCountr, right click on one of the package and add new one , do not forget to give it a new title:

- then proceed to create a new class: to create a new class : put this code in the in text box in the bottom :

```
Object << #MyClass
	slots: { #count };
	sharedVariables: {};
	package: 'www'

```

now as pharo is a language , we need to acces this instance variable and set in it : to get access we need a to put a getter and setter :( known as mutators and accessors )

getter :

```
count 
	^count
```

setter :

```
count: anInteger
	count := anInteger 
```

in this case to get the values from the instance varibles that we create it :

```
Counter new count
>> nil : which is a thevalues null in Pharo
```



to set a value in this varibales we can types this , 

```
c := Counter new count: 7.
c count
>> 7 
```

now in order to make define a bew test class : we should create a new test class called CounterTest

 in this tst class we will have a new methods called testCounIsSetAndRead, this mehtod will test if the values is set and return this value:

 ```
 testCounterIsSetAndRead
	| c | 
	c := Counter new.
	c count: 7.
	self assert:c count equals:7 
 ```

 this method will create first an oject form this class counter thorug h using new, then it will call the method count and put 7 in it it is believed that
 then we it iwll claled the asser tand check through using th egetter that if it really 7 .



 # Increment:

 Now i order to increment this value in the count form 0 to 1 , we implement one method that increment the values in the count from 0 to 1 through this method :

 ```
 increment
    count := count +1
 ```
 

 and in order to decrement the value , we implement another method to decrement the value 


 ```
 decrement 
    count := count -1
 ```


now to test if it is really working we need to implement a testing function to test if both function is really working or no :

```
testIncrement
	| c |
	c := Counter new.
	c count: 0 ; increment ; increment .
	self assert: c count equals: 2
```

```
testDecrement
	| c |
	c := Counter new.
	c count: 0 ; decrement ; decrement .
	self assert: c count equals: -2
```


# initilization 
Now in order to not mess up the testing, we nned to do the initialization, in this initialization , we will create a function to a initialize a function to initialize  the values ot 0.

```
initialize
    count:= 0
```

now in playgroung we execute this code , it should return 1 
```
Counter new increment count 
```

now in order to test if it actually works and we don't get a bug 

```
testCounterWellInitialized
	self 
		assert: (Counter new increment; increment; count )
		equals: 2
```


now i order to define a new instance creation method to understand the difference between the instance side and the class side , we will implement 

this method in the class side to be able to be sent to the class instead of the instance


```
startingAt: anInteger
    ^ self new count: anInteger.
```

and in order to test if it's working:

```
testCounterStartingAt5
    self assert: (Counter startingAt: 5) count equals: 5
```

now in order to checks if everything is working, we will implement this in the test code ( another method )

```
testAlternateCreationMethod
    self assert: ((Counter startingAt: 19) increment ; count) equals: 20
```


for others equestion and for the whole explanatation, you can check this book :
http://rmod-pharo-mooc.lille.inria.fr/MOOC/PharoMOOC/Week1/Exo-Counter.pdf

