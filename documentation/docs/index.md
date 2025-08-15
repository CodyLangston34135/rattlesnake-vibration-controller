# Welcome to Rattlesnake Vibrarion Controller

## Abstract

Rattlesnake is a combined-environments, multiple input/multiple output control system for dynamic excitation of structures under test.  It provides capabilities to control multiple responses on the part using multiple exciters using various control strategies.  Rattlesnake is written in the Python programming language to facilitate multiple input/multiple output vibration research by allowing users to prescribe custom control laws to the controller.  Rattlesnake can target multiple hardware devices, or even perform synthetic control to simulate a test virtually.  Rattlesnake has been used to execute control problems with up to 200 response channels and 24 shaker drives.  This document describes the functionality, architecture, and usage of the Rattlesnake controller to perform combined environments testing.

## Nomenclature

abbreviation | description
--- | ---
6DoF | six degree-of-freedom
API | application programming interface
APSD | auto-power spectral density
CCLD | constant current line drive
COLA | constant overlap and add
CPSD | cross-power spectral density
FEM | finite element model
FFT | fast Fourier transform
FRF | frequency response function
GUI | graphical user interface
ICP | integrated circuit piezoelectric
IDE | integrated development environment
IEPE | integrated electronics piezoelectric
IFFT | inverse fast Fourier transform
JSON | javascript object notation
MIMO | multiple input/multiple output
ReST | representational state transfer
RMS | root-mean-square
SVD | singular value decomposition
TRAC | time response assurance criterion
UI | user interface

## Notation

### Accents

\begin{description}
    \item[$\mathbf{x}$ \normalfont (bold, non-italic typeface)] Matrix or vector
    \item[$x$ \normalfont (non-bold, italic typeface)] Scalar or array
\end{description}


### Variables

### Operations

## Introduction

The field of \ac{MIMO vibration testing has grown substantially in the past few years.  \Ac{MIMO vibration testing provides the capability to match a field environment more accurately and at more locations on the test article than traditional single-axis vibration testing.  Unfortunately, many existing vibration control systems are proprietary, which makes it difficult to implement new \ac{MIMO techniques.  Currently, \ac{MIMO vibration practitioners must either develop a control system from scratch to implement their ideas, or alternatively convince an \ac{MIMO vibration software vendor to implement their ideas into existing devices, and neither of these approaches are conducive to the rapid and iterative nature of research.  The Rattlesnake framework was developed to overcome these limitations and facilitate \ac{MIMO vibration research.  Rattlesnake is a \ac{MIMO control system that provides the user the ability to overcome testing challenges by providing a flexible framework that can be extended and modified to meet testing demands.  Rattlesnake can run multiple environments simultaneously, providing a combined-environments capability that does not yet exist in commercial software packages.  It can target multiple hardware devices, or even perform control virtually using a state space model, \ac{FEM results, or a SDynPy System.

