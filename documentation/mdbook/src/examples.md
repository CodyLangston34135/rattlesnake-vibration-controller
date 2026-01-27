(sec:examples)=
# Examples

There is a significant amount of information contained in this document, which can be incredibly difficult to digest for a new user of the software.  These appendices will therefore contain example problems that users can implement either completely synthetically or using minimal hardware resources to try out Rattlesnake.  These can be used as a kind of quick-start guide to using Rattlesnake.

Appendix \ref{sec:example_nidaqmx} demonstrates how a test can be run using relatively inexpensive NI hardware.

Appendix \ref{sec:example_sdynpy} demonstrates how the same test from Appendix \ref{sec:example_nidaqmx} can be simulated synthetically using SDynPy `System` objects.  This example problem would be a good place to start for users without hardware, as it only relies on software.

Appendix \ref{sec:example_state_space} demonstrates how the same test from Appendix \ref{sec:example_nidaqmx} can be simulated synthetically using State Space matrices.  State space matrices are more flexible than SDynPy `System` objects to represent generic linear time-invariant systems.