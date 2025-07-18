from typing import Iterable
from typing import Iterator

JSON_VALUE = str | bool | int | float | dict[str, "JSON_VALUE"] | list["JSON_VALUE"]


class Path:
    def __init__(self, group_name: str, attr_type: str = "position", suffix: str = "", fps: float = 30.0):
        self.route: list[tuple[float, float, float]] = []
        self.group_name: str = group_name
        self.attr_type: str = attr_type
        self.suffix: str = suffix
        self.fps: float = fps

    def add_waypoint(self, lat: float, lon: float, time: float):
        self.route.append((lat, lon, time))

    def altitudes(self, base_altitude: float = 0.5, altitude_acceleration: float = 0.2) -> Iterator[tuple[float, float]]:
        last_lat, last_lon, last_time = 0, 0, 0
        for i, (lat, lon, time) in enumerate(self.route):
            if i > 0:
                time_delta = (time - last_time) / 2
                yield last_time + time_delta, base_altitude + (time_delta ** 2) * altitude_acceleration / 2
            yield time, base_altitude
            last_lat, last_lon, last_time = lat, lon, time

    def to_esp(self) -> dict[str, JSON_VALUE]:
        first_lat, first_lon, _ = self.route[0]
        return {
            "type": self.group_name,
            "inTimeline": True,
            "attributes": [{
                "type": self.attr_type,
                "inTimeline": True,
                "attributes": [
                    {
                        "type": f"longitude{self.suffix}",
                        "value": {
                            "relative": first_lon
                        },
                        "keyframes": [
                            {
                                "time": time * self.fps,
                                "value": lon
                            }
                            for _, lon, time in self.route
                        ],
                        "inTimeline": True
                    },
                    {
                      "type": f"latitude{self.suffix}",
                      "value": {
                        "relative": first_lat
                      },
                      "keyframes": [
                          {
                              "time": time * self.fps,
                              "value": lat
                          }
                          for lat, _, time in self.route
                      ],
                      "inTimeline": True
                    },
                    {
                        "type": f"altitude{self.suffix}",
                        "value": {
                            "maxValueRange": 65117481,
                            "minValueRange": -500,
                            "relative": 0.5,
                            "logarithmic": True
                        },
                        "keyframes": [
                            {
                                "time": 0,
                                "value": 0.5
                            }
                        ],
                        # "keyframes": [
                        #     {
                        #         "time": time * self.fps,
                        #         "value": value,
                        #         "transitionIn": {
                        #             # "x": -0.09259259259259256,
                        #             # "y": 0.000004379382743779914,
                        #             # "influence": 0.5925925932554184,
                        #             "type": "auto"
                        #         },
                        #         "transitionOut": {
                        #             # "x": 0.09259259259259256,
                        #             # "y": -0.0000043793827438526705,
                        #             # "influence": 0.5925925932554184,
                        #             "type": "auto"
                        #         }
                        #     }
                        #     for time, value in self.altitudes()
                        # ],
                        "inTimeline": True
                    }
                ]
            }]
        }


def make_esp(route: Iterable[tuple[float, float, float]], fps: int = 30, speedup: float = 1.0) -> dict[str, JSON_VALUE]:
    camera_pos = Path("cameraPositionGroup", fps=fps)
    poi_pos = Path("cameraTargetEffect", attr_type="poi", suffix="POI", fps=fps)
    duration_seconds = 0
    for lat, lon, time in route:
        lat = (lat + 90) / 180
        lon = (lon + 180) / 360
        camera_pos.add_waypoint(lat, lon, time / speedup)
        poi_pos.add_waypoint(lat, lon, time / speedup)
        duration_seconds = max(duration_seconds, time / speedup)
        # TODO: Remove this later:
        # if time / speedup >= 10:
        #     break

    duration_frames = int(duration_seconds * fps + 0.5)

    esp = {
        "type": "quickstart",
        "modelVersion": 18,
        "settings": {
            "name": "NYC Subway Tour",
            "frameRate": fps,
            "dimensions": {
                "width": 1920,
                "height": 1080
            },
            "duration": duration_frames,
            "timeFormat": "frames"
        },
        "has_started": True,
        "has_finished": True,
        "playbackManager": {
            "range": {
                "start": 0,
                "end": duration_frames
            }
        },
        "scenes": [{
            "animationModel": {
                "roving": False,
                "logarithmic": True,
                "groupedPosition": True
            },
            "duration": duration_frames,
            "attributes": [
                {
                    "type": "environmentGroup",
                    "attributes": [
                        {
                            "type": "sunGroup",
                            "attributes": [
                                {
                                    "type": "sunVisibility",
                                    "value": {}
                                },
                                {
                                    "type": "worldTime",
                                    "value": {
                                        "maxValueRange": 1737034328557,
                                        "minValueRange": 1736861528557,
                                        "relative": 0.5
                                    }
                                }
                            ]
                        },
                        {
                            "type": "cloudGroup",
                            "attributes": [
                                {
                                    "type": "cloudVisibility",
                                    "value": {}
                                },
                                {
                                    "type": "cloudopacity",
                                    "value": {}
                                },
                                {
                                    "type": "cloudheight",
                                    "value": {}
                                },
                                {
                                    "type": "clouddate",
                                    "value": {
                                        "relative": 1,
                                        "minValueRange": 1736859600000,
                                        "maxValueRange": 1736938800000
                                    }
                                }
                            ]
                        },
                        {
                            "type": "starsPlanetsGroup",
                            "attributes": [
                                {
                                    "type": "starsEnabled",
                                    "value": {}
                                }
                            ]
                        },
                        {
                            "type": "seawaterGroup",
                            "attributes": [
                                {
                                    "type": "seawater",
                                    "value": {}
                                },
                                {
                                    "type": "influence",
                                    "value": {
                                        "relative": 1
                                    }
                                }
                            ]
                        },
                        {
                            "type": "buildingsEnabled",
                            "value": {}
                        }
                    ]
                },
                {
                    "type": "cameraGroup",
                    "inTimeline": True,
                    "attributes": [
                        camera_pos.to_esp(),
                        poi_pos.to_esp(),
                    ]
                }
            ],
            "cameraExport": {
                "logarithmic": True,
                "modelVersion": 2
            }
        }],
    }
    return esp


"""
{
    "type": "quickstart",
    "modelVersion": 18,
    "settings": {
        "name": "NYC Subway Tour",
        "frameRate": 30,
        "dimensions": {
            "width": 1920,
            "height": 1080
        },
        "duration": 480,
        "timeFormat": "frames"
    },
    "scenes": [
        {
            "animationModel": {
                "roving": false,
                "logarithmic": true,
                "groupedPosition": true
            },
            "duration": 480,
            "attributes": [
                {
                    "type": "cameraGroup",
                    "inTimeline": true,
                    "attributes": [
                        {
                            "type": "cameraPositionGroup",
                            "inTimeline": true,
                            "attributes": [
                                {
                                    "type": "position",
                                    "inTimeline": true,
                                    "attributes": [
                                        {
                                            "type": "longitude",
                                            "value": {
                                                "relative": 0.29512500055555557
                                            },
                                            "keyframes": [
                                                {
                                                    "time": 0,
                                                    "value": 0.29512500055555557
                                                },
                                                {
                                                    "time": 0.125,
                                                    "value": 0.29512500055555557,
                                                    "transitionOut": {
                                                        "x": 1,
                                                        "y": 0,
                                                        "influence": 0.2,
                                                        "type": "custom"
                                                    }
                                                },
                                                {
                                                    "time": 0.28125,
                                                    "value": 0.29511400817453626,
                                                    "transitionIn": {
                                                        "x": -0.09259259259259256,
                                                        "y": 0.000004379382743779914,
                                                        "influence": 0.5925925932554184,
                                                        "type": "auto"
                                                    },
                                                    "transitionOut": {
                                                        "x": 0.09259259259259256,
                                                        "y": -0.0000043793827438526705,
                                                        "influence": 0.5925925932554184,
                                                        "type": "auto"
                                                    }
                                                },
                                                {
                                                    "time": 0.4375,
                                                    "value": 0.29510623444433476,
                                                    "transitionIn": {
                                                        "x": -1,
                                                        "y": 0,
                                                        "influence": 0.2,
                                                        "type": "custom"
                                                    }
                                                },
                                                {
                                                    "time": 0.46875,
                                                    "value": 0.29510623444433476
                                                },
                                                {
                                                    "time": 0.5625,
                                                    "value": 0.29510623444433476,
                                                    "transitionOut": {
                                                        "x": 1,
                                                        "y": 0,
                                                        "influence": 0.2,
                                                        "type": "custom"
                                                    }
                                                },
                                                {
                                                    "time": 0.71875,
                                                    "value": 0.2950974477777689,
                                                    "transitionIn": {
                                                        "x": -0.05208333333333337,
                                                        "y": 0.0000029288888552803094,
                                                        "influence": 0.35,
                                                        "type": "auto"
                                                    },
                                                    "transitionOut": {
                                                        "x": 0.05208333333333337,
                                                        "y": -0.0000029288888552803094,
                                                        "influence": 0.35,
                                                        "type": "auto"
                                                    }
                                                },
                                                {
                                                    "time": 0.875,
                                                    "value": 0.29508866111120313,
                                                    "transitionIn": {
                                                        "x": -1,
                                                        "y": 0,
                                                        "influence": 0.2,
                                                        "type": "custom"
                                                    }
                                                },
                                                {
                                                    "time": 1,
                                                    "value": 0.29508866111120313
                                                }
                                            ],
                                            "inTimeline": true
                                        },
                                        {
                                            "type": "latitude",
                                            "value": {
                                                "relative": 0.7255792384213761
                                            },
                                            "keyframes": [
                                                {
                                                    "time": 0,
                                                    "value": 0.7255792384213761
                                                },
                                                {
                                                    "time": 0.125,
                                                    "value": 0.7255792384213761,
                                                    "transitionOut": {
                                                        "x": 1,
                                                        "y": 0,
                                                        "influence": 0.2,
                                                        "type": "custom"
                                                    }
                                                },
                                                {
                                                    "time": 0.28125,
                                                    "value": 0.7255675643841871,
                                                    "transitionIn": {
                                                        "x": -0.09259259259259256,
                                                        "y": 0.0000057920166617320135,
                                                        "influence": 0.5925925937519925,
                                                        "type": "auto"
                                                    },
                                                    "transitionOut": {
                                                        "x": 0.09259259259259256,
                                                        "y": -0.000005792016661689943,
                                                        "influence": 0.5925925937519925,
                                                        "type": "auto"
                                                    }
                                                },
                                                {
                                                    "time": 0.4375,
                                                    "value": 0.7255531750591965,
                                                    "transitionIn": {
                                                        "x": -1,
                                                        "y": 0,
                                                        "influence": 0.2,
                                                        "type": "custom"
                                                    }
                                                },
                                                {
                                                    "time": 0.46875,
                                                    "value": 0.7255531750591965
                                                },
                                                {
                                                    "time": 0.5625,
                                                    "value": 0.7255531750591965,
                                                    "transitionOut": {
                                                        "x": 1,
                                                        "y": 0,
                                                        "influence": 0.2,
                                                        "type": "custom"
                                                    }
                                                },
                                                {
                                                    "time": 0.71875,
                                                    "value": 0.7255419517135142,
                                                    "transitionIn": {
                                                        "x": -0.05208333333333337,
                                                        "y": 0.0000037411152274957615,
                                                        "influence": 0.35,
                                                        "type": "auto"
                                                    },
                                                    "transitionOut": {
                                                        "x": 0.05208333333333337,
                                                        "y": -0.0000037411152274957615,
                                                        "influence": 0.35,
                                                        "type": "auto"
                                                    }
                                                },
                                                {
                                                    "time": 0.875,
                                                    "value": 0.725530728367832,
                                                    "transitionIn": {
                                                        "x": -1,
                                                        "y": 0,
                                                        "influence": 0.2,
                                                        "type": "custom"
                                                    }
                                                },
                                                {
                                                    "time": 1,
                                                    "value": 0.725530728367832
                                                }
                                            ],
                                            "inTimeline": true
                                        },
                                        {
                                            "type": "altitude",
                                            "value": {
                                                "maxValueRange": 65117481,
                                                "minValueRange": -500,
                                                "relative": 0.47828134579086,
                                                "logarithmic": true
                                            },
                                            "keyframes": [
                                                {
                                                    "time": 0,
                                                    "value": 0.47828134579086
                                                },
                                                {
                                                    "time": 0.125,
                                                    "value": 0.47828134579086,
                                                    "transitionOut": {
                                                        "x": 1,
                                                        "y": 0,
                                                        "influence": 0.2,
                                                        "type": "custom"
                                                    }
                                                },
                                                {
                                                    "time": 0.28125,
                                                    "value": 0.503815721193825,
                                                    "transitionIn": {
                                                        "x": -0.09259259259259256,
                                                        "y": 0.000019320724452542848,
                                                        "influence": 0.35,
                                                        "type": "auto"
                                                    },
                                                    "transitionOut": {
                                                        "x": 0.09259259259259256,
                                                        "y": -0.000019320724452542848,
                                                        "influence": 0.35,
                                                        "type": "auto"
                                                    }
                                                },
                                                {
                                                    "time": 0.4375,
                                                    "value": 0.478165421444145,
                                                    "transitionIn": {
                                                        "x": -1,
                                                        "y": 0,
                                                        "influence": 0.2,
                                                        "type": "custom"
                                                    }
                                                },
                                                {
                                                    "time": 0.46875,
                                                    "value": 0.478165421444145
                                                },
                                                {
                                                    "time": 0.5625,
                                                    "value": 0.478165421444145,
                                                    "transitionOut": {
                                                        "x": 1,
                                                        "y": 0,
                                                        "influence": 0.2,
                                                        "type": "custom"
                                                    }
                                                },
                                                {
                                                    "time": 0.71875,
                                                    "value": 0.501999257684734,
                                                    "transitionIn": {
                                                        "x": -0.05208333333333337,
                                                        "y": 0.000016395010984382452,
                                                        "influence": 0.35,
                                                        "type": "auto"
                                                    },
                                                    "transitionOut": {
                                                        "x": 0.05208333333333337,
                                                        "y": -0.000016395010984382452,
                                                        "influence": 0.35,
                                                        "type": "auto"
                                                    }
                                                },
                                                {
                                                    "time": 0.875,
                                                    "value": 0.478067051378239,
                                                    "transitionIn": {
                                                        "x": -1,
                                                        "y": 0,
                                                        "influence": 0.2,
                                                        "type": "custom"
                                                    }
                                                },
                                                {
                                                    "time": 1,
                                                    "value": 0.478067051378239
                                                }
                                            ],
                                            "inTimeline": true
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            "type": "cameraTargetEffect",
                            "inTimeline": true,
                            "attributes": [
                                {
                                    "type": "enabled",
                                    "value": {
                                        "relative": 1
                                    },
                                    "keyframes": [
                                        {
                                            "time": 0.01875,
                                            "value": 1,
                                            "transitionIn": {
                                                "x": 0,
                                                "y": 0,
                                                "type": "auto"
                                            },
                                            "transitionOut": {
                                                "x": 0,
                                                "y": 0,
                                                "type": "auto"
                                            }
                                        }
                                    ],
                                    "inTimeline": true
                                },
                                {
                                    "type": "poi",
                                    "inTimeline": true,
                                    "attributes": [
                                        {
                                            "type": "longitudePOI",
                                            "value": {
                                                "relative": 0.2951250040552956
                                            },
                                            "keyframes": [
                                                {
                                                    "time": 0,
                                                    "value": 0.2951250040552956
                                                },
                                                {
                                                    "time": 0.125,
                                                    "value": 0.29511403680065695,
                                                    "transitionIn": {
                                                        "x": -0.027195070569107176,
                                                        "y": 5.701794631755572E-7,
                                                        "influence": 0.21756056460067558,
                                                        "type": "auto"
                                                    },
                                                    "transitionOut": {
                                                        "x": 0.09518274699187512,
                                                        "y": -0.000001995628121087556,
                                                        "influence": 0.21756056460067558,
                                                        "type": "auto"
                                                    }
                                                },
                                                {
                                                    "time": 0.5625,
                                                    "value": 0.2951062344443501,
                                                    "transitionIn": {
                                                        "x": -0.10937500000000001,
                                                        "y": 0.000002986192703280377,
                                                        "influence": 0.2500000000931772,
                                                        "type": "auto"
                                                    },
                                                    "transitionOut": {
                                                        "x": 0.078125,
                                                        "y": -0.0000021329947880811647,
                                                        "influence": 0.2500000000931772,
                                                        "type": "auto"
                                                    }
                                                },
                                                {
                                                    "time": 0.875,
                                                    "value": 0.2950886611111976,
                                                    "transitionIn": {
                                                        "x": -1,
                                                        "y": 0,
                                                        "influence": 0.5,
                                                        "type": "custom"
                                                    },
                                                    "transitionOut": {
                                                        "x": 0.07291666666666663,
                                                        "y": 5.551115123125783E-17,
                                                        "influence": 0.35,
                                                        "type": "auto"
                                                    }
                                                },
                                                {
                                                    "time": 1,
                                                    "value": 0.2950886611111976
                                                }
                                            ],
                                            "inTimeline": true
                                        },
                                        {
                                            "type": "latitudePOI",
                                            "value": {
                                                "relative": 0.7255792653729498
                                            },
                                            "keyframes": [
                                                {
                                                    "time": 0,
                                                    "value": 0.7255792653729498
                                                },
                                                {
                                                    "time": 0.125,
                                                    "value": 0.7255675898410978,
                                                    "transitionIn": {
                                                        "x": -0.031242449075643868,
                                                        "y": 6.664153181108832E-7,
                                                        "influence": 0.24993959266201068,
                                                        "type": "auto"
                                                    },
                                                    "transitionOut": {
                                                        "x": 0.10934857176475353,
                                                        "y": -0.0000023324536133628726,
                                                        "influence": 0.24993959266201068,
                                                        "type": "auto"
                                                    }
                                                },
                                                {
                                                    "time": 0.5625,
                                                    "value": 0.7255531938968682,
                                                    "transitionIn": {
                                                        "x": -0.031249999999999997,
                                                        "y": 0.0000029596738130299727,
                                                        "influence": 0.07142857174892503,
                                                        "type": "auto"
                                                    },
                                                    "transitionOut": {
                                                        "x": 0.02232142857142857,
                                                        "y": -0.000002114052723594946,
                                                        "influence": 0.07142857174892503,
                                                        "type": "auto"
                                                    }
                                                },
                                                {
                                                    "time": 0.875,
                                                    "value": 0.725530747412628,
                                                    "transitionIn": {
                                                        "x": -1,
                                                        "y": 0,
                                                        "influence": 0.5,
                                                        "type": "custom"
                                                    },
                                                    "transitionOut": {
                                                        "x": 0.07291666666666663,
                                                        "y": -1.1102230246251565E-16,
                                                        "influence": 0.35,
                                                        "type": "auto"
                                                    }
                                                },
                                                {
                                                    "time": 1,
                                                    "value": 0.725530747412628
                                                }
                                            ],
                                            "inTimeline": true
                                        },
                                        {
                                            "type": "altitudePOI",
                                            "value": {
                                                "maxValueRange": 65117481,
                                                "minValueRange": -500,
                                                "relative": 0.456988566432049,
                                                "logarithmic": true
                                            },
                                            "keyframes": [
                                                {
                                                    "time": 0,
                                                    "value": 0.456988566432049
                                                },
                                                {
                                                    "time": 0.125,
                                                    "value": 0.456988566432049,
                                                    "transitionOut": {
                                                        "x": 1,
                                                        "y": 0,
                                                        "influence": 0.5,
                                                        "type": "custom"
                                                    }
                                                },
                                                {
                                                    "time": 0.5625,
                                                    "value": 0.456933317998392,
                                                    "transitionOut": {
                                                        "x": 1,
                                                        "y": 0,
                                                        "influence": 0.5,
                                                        "type": "custom"
                                                    }
                                                },
                                                {
                                                    "time": 0.875,
                                                    "value": 0.456416902436951,
                                                    "transitionIn": {
                                                        "x": -1,
                                                        "y": 0,
                                                        "influence": 0.5,
                                                        "type": "custom"
                                                    },
                                                    "transitionOut": {
                                                        "x": 0.07291666666666663,
                                                        "y": 0,
                                                        "influence": 0.35,
                                                        "type": "auto"
                                                    }
                                                },
                                                {
                                                    "time": 1,
                                                    "value": 0.456416902436951
                                                }
                                            ],
                                            "inTimeline": true
                                        }
                                    ]
                                },
                                {
                                    "type": "influence",
                                    "value": {
                                        "relative": 0
                                    },
                                    "keyframes": [
                                        {
                                            "time": 0,
                                            "value": 0
                                        },
                                        {
                                            "time": 0.125,
                                            "value": 0,
                                            "transitionOut": {
                                                "x": 1,
                                                "y": 0,
                                                "influence": 0.2,
                                                "type": "custom"
                                            }
                                        },
                                        {
                                            "time": 0.28125,
                                            "value": 0,
                                            "transitionIn": {
                                                "x": -1,
                                                "y": 0,
                                                "influence": 0.5,
                                                "type": "custom"
                                            },
                                            "transitionOut": {
                                                "x": 1,
                                                "y": 0,
                                                "influence": 0.5,
                                                "type": "custom"
                                            }
                                        },
                                        {
                                            "time": 0.4375,
                                            "value": 0,
                                            "transitionIn": {
                                                "x": -1,
                                                "y": 0,
                                                "influence": 0.2,
                                                "type": "custom"
                                            }
                                        },
                                        {
                                            "time": 0.5625,
                                            "value": 0,
                                            "transitionOut": {
                                                "x": 1,
                                                "y": 0,
                                                "influence": 0.2,
                                                "type": "custom"
                                            }
                                        },
                                        {
                                            "time": 0.71875,
                                            "value": 0,
                                            "transitionIn": {
                                                "x": -1,
                                                "y": 0,
                                                "influence": 0.5,
                                                "type": "custom"
                                            },
                                            "transitionOut": {
                                                "x": 1,
                                                "y": 0,
                                                "influence": 0.5,
                                                "type": "custom"
                                            }
                                        },
                                        {
                                            "time": 0.875,
                                            "value": 0,
                                            "transitionIn": {
                                                "x": -1,
                                                "y": 0,
                                                "influence": 0.2,
                                                "type": "custom"
                                            }
                                        },
                                        {
                                            "time": 1,
                                            "value": 0
                                        }
                                    ],
                                    "inTimeline": true
                                }
                            ]
                        },
                        {
                            "type": "cameraRotationGroup",
                            "inTimeline": true,
                            "attributes": [
                                {
                                    "type": "rotationX",
                                    "value": {},
                                    "keyframes": [
                                        {
                                            "time": 0,
                                            "value": 0
                                        },
                                        {
                                            "time": 0.125,
                                            "value": 0,
                                            "transitionOut": {
                                                "x": 1,
                                                "y": 0,
                                                "influence": 0.2,
                                                "type": "custom"
                                            }
                                        },
                                        {
                                            "time": 0.4375,
                                            "value": 0,
                                            "transitionIn": {
                                                "x": -1,
                                                "y": 0,
                                                "influence": 0.2,
                                                "type": "custom"
                                            }
                                        },
                                        {
                                            "time": 0.5625,
                                            "value": 0,
                                            "transitionOut": {
                                                "x": 1,
                                                "y": 0,
                                                "influence": 0.2,
                                                "type": "custom"
                                            }
                                        },
                                        {
                                            "time": 0.875,
                                            "value": 0,
                                            "transitionIn": {
                                                "x": -1,
                                                "y": 0,
                                                "influence": 0.2,
                                                "type": "custom"
                                            }
                                        },
                                        {
                                            "time": 1,
                                            "value": 0
                                        }
                                    ],
                                    "inTimeline": true
                                },
                                {
                                    "type": "rotationY",
                                    "value": {},
                                    "keyframes": [
                                        {
                                            "time": 0,
                                            "value": 0
                                        },
                                        {
                                            "time": 0.125,
                                            "value": 0,
                                            "transitionOut": {
                                                "x": 1,
                                                "y": 0,
                                                "influence": 0.2,
                                                "type": "custom"
                                            }
                                        },
                                        {
                                            "time": 0.4375,
                                            "value": 0,
                                            "transitionIn": {
                                                "x": -1,
                                                "y": 0,
                                                "influence": 0.2,
                                                "type": "custom"
                                            }
                                        },
                                        {
                                            "time": 0.5625,
                                            "value": 0,
                                            "transitionOut": {
                                                "x": 1,
                                                "y": 0,
                                                "influence": 0.2,
                                                "type": "custom"
                                            }
                                        },
                                        {
                                            "time": 0.875,
                                            "value": 0,
                                            "transitionIn": {
                                                "x": -1,
                                                "y": 0,
                                                "influence": 0.2,
                                                "type": "custom"
                                            }
                                        },
                                        {
                                            "time": 1,
                                            "value": 0
                                        }
                                    ],
                                    "inTimeline": true
                                },
                                {
                                    "type": "rotationZ",
                                    "value": {}
                                }
                            ]
                        },
                        {
                            "type": "cameraLensGroup",
                            "attributes": [
                                {
                                    "type": "fov",
                                    "value": {}
                                },
                                {
                                    "type": "exposure",
                                    "value": {}
                                },
                                {
                                    "type": "aperture",
                                    "value": {}
                                },
                                {
                                    "type": "minFocusLength",
                                    "value": {}
                                }
                            ]
                        }
                    ]
                },
                {
                    "type": "environmentGroup",
                    "attributes": [
                        {
                            "type": "sunGroup",
                            "attributes": [
                                {
                                    "type": "sunVisibility",
                                    "value": {}
                                },
                                {
                                    "type": "worldTime",
                                    "value": {
                                        "maxValueRange": 1737034328557,
                                        "minValueRange": 1736861528557,
                                        "relative": 0.5
                                    }
                                }
                            ]
                        },
                        {
                            "type": "cloudGroup",
                            "attributes": [
                                {
                                    "type": "cloudVisibility",
                                    "value": {}
                                },
                                {
                                    "type": "cloudopacity",
                                    "value": {}
                                },
                                {
                                    "type": "cloudheight",
                                    "value": {}
                                },
                                {
                                    "type": "clouddate",
                                    "value": {
                                        "relative": 1,
                                        "minValueRange": 1736859600000,
                                        "maxValueRange": 1736938800000
                                    }
                                }
                            ]
                        },
                        {
                            "type": "starsPlanetsGroup",
                            "attributes": [
                                {
                                    "type": "starsEnabled",
                                    "value": {}
                                }
                            ]
                        },
                        {
                            "type": "seawaterGroup",
                            "attributes": [
                                {
                                    "type": "seawater",
                                    "value": {}
                                },
                                {
                                    "type": "influence",
                                    "value": {
                                        "relative": 1
                                    }
                                }
                            ]
                        },
                        {
                            "type": "buildingsEnabled",
                            "value": {}
                        }
                    ]
                }
            ],
            "cameraExport": {
                "logarithmic": true,
                "modelVersion": 2
            }
        }
    ],
    "has_started": true,
    "has_finished": true,
    "playbackManager": {
        "range": {
            "start": 0,
            "end": 480
        }
    }
}
"""