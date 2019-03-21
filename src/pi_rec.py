import os

import numpy as np
from torch.utils.data import DataLoader
from .dataset import Dataset
from .models import G_Model
from .utils import resize, create_dir, imsave, to_tensor, output_align


class PiRec():
    def __init__(self, config):
        self.config = config

        self.debug = False
        self.g_model = G_Model(config).to(config.DEVICE)

        # test mode
        if self.config.MODE == 2:
            self.test_dataset = Dataset(config, config.TEST_FLIST,
                                        augment=False, training=False)

        # self.samples_path = os.path.join(config.PATH, 'samples')
        self.results_path = os.path.join(config.PATH, 'results')
        self.results_path = os.path.join(self.results_path, 'km_{}_sigma_{}'.format(config.KM, config.SIGMA))

        if config.RESULTS is not None:
            self.results_path = os.path.join(config.RESULTS)

        if config.DEBUG is not None and config.DEBUG != 0:
            self.debug = True

    def load(self):
        self.g_model.load()

    def test(self):
        self.g_model.eval()

        create_dir(self.results_path)

        test_loader = DataLoader(
            dataset=self.test_dataset,
            batch_size=1,
        )

        index = 0
        for items in test_loader:
            name = self.test_dataset.load_name(index)
            images, images_gray, edges, images_blur = self.cuda(*items)
            # print('images size is {}, \n edges size is {}, \n images_blur size is {}'.format(images.size(), edges.size(), images_blur.size()))
            index += 1

            outputs = self.g_model(images, edges, images_blur)
            outputs = output_align(images, outputs)
            outputs_merged = outputs

            output = self.postprocess(outputs_merged)[0]
            path = os.path.join(self.results_path, name)
            print(index, name)

            imsave(output, path)

            if self.debug:
                images_input = self.postprocess(images)[0]
                edges = self.postprocess(edges)[0]
                images_blur = self.postprocess(images_blur)[0]
                fname, fext = name.split('.')
                fext = 'png'
                imsave(images_input, os.path.join(self.results_path, fname + '_input.' + fext))
                imsave(edges, os.path.join(self.results_path, fname + '_edge.' + fext))
                imsave(images_blur, os.path.join(self.results_path, fname + '_color_domain.' + fext))

        print('\nEnd test....')

    def draw(self, color_domain, edge):
        self.g_model.eval()
        size = self.config.INPUT_SIZE
        color_domain = resize(color_domain, size, size, interp='lanczos')
        edge = resize(edge, size, size, interp='lanczos')
        edge[edge <= 69] = 0
        edge[edge > 69] = 255

        color_domain = to_tensor(color_domain)
        edge = to_tensor(edge)

        color_domain, edge = self.cuda(color_domain, edge)

        if self.config.DEBUG:
            print('In model.draw():---> \n color domain size is {}, edges size is {}'.format(color_domain.size(),
                                                                                             edge.size()))

        outputs = self.g_model(None, edge, color_domain)

        outputs = self.postprocess(outputs)[0]
        output = outputs.cpu().numpy().astype(np.uint8).squeeze()
        edge = self.postprocess(edge)[0]
        edge = edge.cpu().numpy().astype(np.uint8).squeeze()

        return output

    def cuda(self, *args):
        return (item.to(self.config.DEVICE) for item in args)

    def postprocess(self, img):
        # [0, 1] => [0, 255]
        img = img * 255.0
        img = img.permute(0, 2, 3, 1)
        return img.int()
