import Energyplus
from queue import Queue, Full, Empty
import numpy as np
import Config

class EnergyPlusEnvironment:
    def __init__(self, cfg: Config.config) -> None:
        self.cfg = cfg
        self.episode = -1
        self.timestep = 0

        self.last_obs = {}
        self.obs_queue = None # this queue and the energyplus's queue is the same obj
        self.act_queue = None # this queue and the energyplus's queue is the same obj
        self.energyplus: Energyplus.EnergyPlus= Energyplus.EnergyPlus(None,None)

        # observation space is a two dimentional array
        # the firt is the action variable
        # the second is the action avaliable values
        self.observation_space_size = len(self.energyplus.variables) + len(self.energyplus.meters)
        # choose one value from every variable
        self.action_space_size = self.energyplus.action_space_size

    # return a first observation
    def reset(self, file_suffix = "defalut"):
        self.episode += 1
        # self.last_obs = self.sample()

        if self.energyplus is not None:
            self.energyplus.stop()
        
        self.obs_queue = Queue(maxsize = 1)
        self.act_queue = Queue(maxsize = 1)

        self.energyplus = Energyplus.EnergyPlus(
            obs_queue = self.obs_queue,
            act_queue = self.act_queue
        )

        self.energyplus.start(file_suffix)

        obs = self.obs_queue.get()
        self.last_obs = obs
        return np.array(list(obs.values()))
    
    # predict next observation
    def step(self, action):
        self.timestep += 1
        done = False

        if self.energyplus.failed():
            raise RuntimeError(f"E+ failed {self.energyplus.sim_results['exit_code']}")
        
        if self.energyplus.simulation_complete:
            done = True
            obs  = self.last_obs
        else:
            timeout = 2
            try:
                self.act_queue.put(action,timeout=timeout)
                self.last_obs = obs = self.obs_queue.get(timeout=timeout)
            except(Full, Empty):
                done = True
                obs = self.last_obs
        
        reward = self.get_reward()
        obs_vec = np.array(list(obs.values()))
        return obs_vec, reward, done

    def get_reward(self):

        # according to the meters and variables to compute
        obs = self.last_obs
        
        # compute the temperature reward
        temp_reward = 0
        temps = ["zone_air_temp_"+str(i+1) for i in range(5)]
        occups = ["people_"+str(i+1) for i in range(5)]
        temps_vals = []
        occups_vals = []
        for temp in temps:
            temps_vals.append(obs[temp])
        for occup in occups:
            occups_vals.append(obs[occup])
        
        for i in range(len(temps_vals)):
            if occups_vals[i] <= 0.001:
                temp_reward += 0
            elif self.cfg.T_MIN <= temps_vals[i] <= self.cfg.T_MAX:
                temp_reward += 0
            elif temps_vals[i] < self.cfg.T_MIN :
                temp_reward += temps_vals[i] - self.cfg.T_MIN
            else:
                temp_reward += self.cfg.T_MAX - temps_vals[i]
        
        # electricity reward
        elec_reward = 0
        elec = obs["elec_cooling"] + obs["gas_heating"]
        elec_reward = - elec/1000

        return temp_reward*1000 + elec_reward
    

    def sample(self):
        # random sample
        np.random.randint(0, len(self.action_space))
        

    def close(self):
        if self.energyplus is not None:
            self.energyplus.stop()

        

