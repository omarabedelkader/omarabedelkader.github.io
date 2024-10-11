---
title: ''
date: 2024-09-12
permalink: /posts/2024/09/blog-post-4/
tags:
  - Pharo
  - Smalltalk
  - Beginner
---

# Pharo OOP Exercises:

## Exercise: My Counter

1. **Create a package**: Name it `MyCounter`. Right-click on an existing package and add a new one, providing an appropriate title.
   
2. **Create a new class**: Add the following code to create a class:

    ```smalltalk
    Object subclass: #Counter
        slots: { #count }.
        sharedVariables: {}.
        package: 'MyCounter'.
    ```

3. **Accessing instance variables**: Pharo uses getter and setter methods (accessors and mutators) to access instance variables.

    - **Getter**: 
      ```smalltalk
      count 
          ^count
      ```

    - **Setter**: 
      ```smalltalk
      count: anInteger
          count := anInteger
      ```

4. **Testing instance variables**: 
   
   - To get the value of `count`:
     ```smalltalk
     Counter new count
     ```

     This will return `nil` as it's the default null value in Pharo.
   
   - To set a value:
     ```smalltalk
     c := Counter new.
     c count: 7.
     c count. "Returns 7"
     ```

## Creating a Test Class

1. **Create a test class `CounterTest`**. In this class, define a method to test setting and reading the count:

    ```smalltalk
    testCounterIsSetAndRead
        | c | 
        c := Counter new.
        c count: 7.
        self assert: c count equals: 7.
    ```

   This method:
   - Creates a `Counter` instance.
   - Sets the count to 7.
   - Asserts that the count is correctly set.

## Increment and Decrement Methods

1. **Increment**: Define a method to increase the count:
   
    ```smalltalk
    increment
        count := count + 1.
    ```

2. **Decrement**: Define a method to decrease the count:
   
    ```smalltalk
    decrement
        count := count - 1.
    ```

3. **Testing increment/decrement**:

    ```smalltalk
    testIncrement
        | c |
        c := Counter new.
        c count: 0 ; increment ; increment.
        self assert: c count equals: 2.
    ```

    ```smalltalk
    testDecrement
        | c |
        c := Counter new.
        c count: 0 ; decrement ; decrement.
        self assert: c count equals: -2.
    ```

## Initialization

1. **Initialize method**: To reset the count, add an initialization method:
   
    ```smalltalk
    initialize
        count := 0.
    ```

2. **Verify initialization**:
   
   - In Playground, execute:
     ```smalltalk
     Counter new increment count.
     ```
     This should return `1`.

3. **Test initialization**:

    ```smalltalk
    testCounterWellInitialized
        self assert: (Counter new increment ; increment ; count) equals: 2.
    ```

## Alternate Instance Creation

1. **Create a method on the class side** to initialize `Counter` with a given value:

    ```smalltalk
    startingAt: anInteger
        ^ self new count: anInteger.
    ```

2. **Test alternate creation**:
   
    ```smalltalk
    testCounterStartingAt5
        self assert: (Counter startingAt: 5) count equals: 5.
    ```

3. **Check alternate creation method**:

    ```smalltalk
    testAlternateCreationMethod
        self assert: ((Counter startingAt: 19) increment ; count) equals: 20.
    ```

### Further Reading

For more detailed exercises and explanations, refer to the Pharo MOOC book: [Pharo Counter Exercise](http://rmod-pharo-mooc.lille.inria.fr/MOOC/PharoMOOC/Week1/Exo-Counter.pdf)
"""



[Download Pharo_Counter_Exercises.md](sandbox:/mnt/data/Pharo_Counter_Exercises.md)




## Exercise : Stone Paper Scissors
### Step 1: Understanding the Problem
The problem uses the "Rock, Paper, Scissors" game to introduce how objects interact based on their types without explicit conditionals. It uses double dispatch, where an object sends a message (method call) to another object to determine the result of their interaction.

### Step 2: Creating the Classes
We need three main classes: `Stone`, `Paper`, and `Scissors`. Each class represents a player in the game, and their interaction determines who wins, loses, or if it's a draw.

```smalltalk
Object subclass: #Stone
    instanceVariableNames: ''
    classVariableNames: ''
    poolDictionaries: ''
    category: 'StonePaperScissors'.

Object subclass: #Paper
    instanceVariableNames: ''
    classVariableNames: ''
    poolDictionaries: ''
    category: 'StonePaperScissors'.

Object subclass: #Scissors
    instanceVariableNames: ''
    classVariableNames: ''
    poolDictionaries: ''
    category: 'StonePaperScissors'.
```

### Step 3: Adding the `play:` Method
This method will be the starting point of the interaction. Each class will define this method to decide what to do when playing against another object.

1. **For `Stone`:**
   - The `play:` method delegates the interaction to the other object's method (double dispatch).
   
   ```smalltalk
   Stone >> play: anotherTool
       ^ anotherTool playAgainstStone: self
   ```

2. **For `Paper`:**
   ```smalltalk
   Paper >> play: anotherTool
       ^ anotherTool playAgainstPaper: self
   ```

3. **For `Scissors`:**
   ```smalltalk
   Scissors >> play: anotherTool
       ^ anotherTool playAgainstScissors: self
   ```

### Step 4: Adding the `playAgainst...` Methods
The second part of the interaction happens when the `playAgainst...` methods are called. Each class will respond differently based on what they're playing against.

#### `Stone` class responses:
```smalltalk
Stone >> playAgainstStone: aStone
    ^ #draw.

Stone >> playAgainstPaper: aPaper
    ^ #paper.

Stone >> playAgainstScissors: aScissors
    ^ #stone.
```
- **Stone vs. Stone**: It's a draw.
- **Stone vs. Paper**: Paper wins.
- **Stone vs. Scissors**: Stone wins.

#### `Paper` class responses:
```smalltalk
Paper >> playAgainstStone: aStone
    ^ #paper.

Paper >> playAgainstPaper: aPaper
    ^ #draw.

Paper >> playAgainstScissors: aScissors
    ^ #scissors.
```
- **Paper vs. Stone**: Paper wins.
- **Paper vs. Paper**: It's a draw.
- **Paper vs. Scissors**: Scissors win.

#### `Scissors` class responses:
```smalltalk
Scissors >> playAgainstStone: aStone
    ^ #stone.

Scissors >> playAgainstPaper: aPaper
    ^ #scissors.

Scissors >> playAgainstScissors: aScissors
    ^ #draw.
```
- **Scissors vs. Stone**: Stone wins.
- **Scissors vs. Paper**: Scissors win.
- **Scissors vs. Scissors**: It's a draw.

### Step 5: Test Cases
The test cases validate that the game logic is working correctly. Here are some example tests:

```smalltalk
StonePaperScissorsTest >> testStoneAgainstPaperIsWinning
    self assert: (Stone new play: Paper new) equals: #paper.

StonePaperScissorsTest >> testScissorAgainstPaperIsWinning
    self assert: (Scissors new play: Paper new) equals: #scissors.

StonePaperScissorsTest >> testStoneAgainstStone
    self assert: (Stone new play: Stone new) equals: #draw.

StonePaperScissorsTest >> testStoneAgainstScissorsIsWinning
    self assert: (Stone new play: Scissors new) equals: #stone.

StonePaperScissorsTest >> testScissorAgainstStoneIsLosing
    self assert: (Scissors new play: Stone new) equals: #stone.

StonePaperScissorsTest >> testPaperAgainstScissorIsLosing
    self assert: (Paper new play: Scissors new) equals: #scissors.

StonePaperScissorsTest >> testPaperAgainstStoneIsWinning
    self assert: (Paper new play: Stone new) equals: #paper.
```

### Step 6: Explanation of Double Dispatch
Double dispatch works by first using the `play:` method to delegate the decision-making to the other object involved in the interaction. This is the first dispatch. The second dispatch occurs when the other object, now knowing what it's playing against, decides on the outcome by calling a `playAgainst...` method. This allows the game logic to be determined by the combination of both objects' types without using conditionals.

For example:
- `Stone new play: Paper new` first calls `play:` on `Stone`, which then calls `playAgainstStone:` on `Paper`. Since `Paper` knows it's playing against `Stone`, it returns `#paper` as the winner.

### Step 7: Conclusion
This design follows the "Don't ask, tell" principle, where instead of asking about the state or type of objects and using conditionals, you delegate responsibility to the objects themselves. Each object "knows" how to respond when faced with another type of object.

By organizing the logic in this way:
- **Encapsulation** is preserved, as each class only handles its own logic.
- **Extensibility** is easier, as adding new elements (e.g., `Lizard` or `Spock` for an extended version of the game) would involve adding new methods without altering the existing ones.

This approach leads to a clean, modular, and maintainable code structure for handling multi-object interactions in object-oriented programming.