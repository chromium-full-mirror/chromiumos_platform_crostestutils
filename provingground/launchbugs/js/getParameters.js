//  Copyright 2022 The ChromiumOS Authors
//  Use of this source code is governed by a BSD-style license that can be
//  found in the LICENSE file.
const TeamId = {
  Commercial: '2018047913735',
  Consumer: '1920469030069',
  Developer: '2185535768207',
  Fundamentals: '1417945292682',
  Trust_Safety: '1488691098512',
  Flex: '1457609259434',
  Platform_Device: '1346066282',
  Platform_Foundations: '2080565135586',
  Devices_Peripherals: '1579017816064',
  ChromeOS:'1346058396'
}

function GetURLParameter(sParam) {
  var sPageURL = window.location.search.substring(1);
  var sURLVariables = sPageURL.split('&');
  for (var i = 0; i < sURLVariables.length; i++) {
    //If param is help return help string
    if (sParam == 'help'){
      if (sURLVariables[i]== 'help')
        return 'help'
    }
    var sParameterName = sURLVariables[i].split('=');
    if (sParameterName[0] == sParam) {
      return sParameterName[1];
    }
  }
}

function GetTeamId(team){
  switch (team) {
      case 'comm':
          return TeamId.Commercial
      case 'cons':
          return TeamId.Consumer
      case 'dev':
          return TeamId.Developer
      case 'fund':
          return TeamId.Fundamentals
      case 'tands':
          return TeamId.Trust_Safety
      case 'flex':
          return TeamId.Flex
      case 'pdev':
          return TeamId.Platform_Device
      case 'pfound':
          return TeamId.Platform_Foundations
      case 'peri':
          return TeamId.Devices_Peripherals
      default:
          return TeamId.ChromeOS
  }
}