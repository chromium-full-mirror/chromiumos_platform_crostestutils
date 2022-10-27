# Launchbugs Redirect

## Launchbugs -- Launch
launchbugs.html is a helper that opens filtered launchbugs based on Milestones,
Test Engineers, and EngProd Bit Approvers on go/launch

## Launchbugs Old -- Monorail
launchbugsold.html is a helper that opens filtered launchbugs based on
Milestones, Test Engineers, Status, and Components on Monorail

## Usage

### Launch
Navigate to go/launchbugs?
Filter by Milestone: go/launchbugs?m=105
Filter by Test Engineers: go/launchbugs?te=dhaddock
Filter by Team: go/launchbugs?team=coreX
Filter by Engprod Approvers: go/launchbugs?a=dhaddock
Filter by Multiple Ldaps: go/launchbugs?te=dhadock,awendy&a=dhadock,awendy
Filter by Unassigned Launches for a given Milestone: go/launchbugs?te=new&m=109

### Monorail
Navigate to go/launchbugsold?
Filter by Milestone: go/launchbugsold?m=105
Filter by Test Engineers: go/launchbugsold?te=dhaddock
Filter by Status: go/launchbugsold?m=105&s=Fixed
Filter by Component IIRC: go/launchbugsold?c=UI>Shell>StatusArea
Filter by Team: go/launchbugsold?team=coreX

### Filtering by Team
Team is not an existing Filter Attribute. The functionality was added to
shorten the Tests Engineers required if we want to add all the TEs from CoreX.
Ex: `go/launchbugs?m=100&team=coreX` will search for all the Launch Bugs in
Milestone 100 where the TEs are dhaddock,kyleshima,hyungtaekim, or awendy

### Testing
After modifying the script, please make sure that the old functionalities are
still working

Some good urls to test in Launch:
- go/launchbugs?
- go/launchbugs?te=new
- go/launchbugs?m=105
- go/launchbugs?m=105&te=dhaddock
- go/launchbugs?te=dhaddock
- go/launchbugs?team=corex
- go/launchbugs?a=dhaddock
- go/launchbugs?team=corex&m=105

Some good urls to test in Monorail:
- go/launchbugsold?
- go/launchbugsold?te=new
- go/launchbugsold?m=105
- go/launchbugsold?m=105&te=dhaddock
- go/launchbugsold?te=dhaddock
- go/launchbugsold?team=corex
- go/launchbugsold?team=corex&m=105
- go/launchbugsold?&m=101&te=dhaddock&s=Fixed
- go/launchbugsold?team=corex&m=101&te=sdantuluri&status=Fixed&c=OS>Systems>Update
