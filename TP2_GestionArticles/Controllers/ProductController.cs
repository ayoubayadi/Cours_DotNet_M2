using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Rendering; 
using TP2_GestionArticles.Models; 
using TP2_GestionArticles.Models.Repositories;
using TP2_GestionArticles.ViewModels;
using System.IO;

namespace TP2_GestionArticles.Controllers
{
    public class ProductController : Controller
    {
        readonly IProductRepository ProductRepository;
        readonly ICategorieRepository CategRepository;
        private readonly IWebHostEnvironment hostingEnvironment;

        // Constructor injection
        public ProductController(IProductRepository ProdRepository, ICategorieRepository categRepository , IWebHostEnvironment hostingEnvironment)
        {
            ProductRepository = ProdRepository;
            CategRepository = categRepository;
            this.hostingEnvironment = hostingEnvironment;
        }

        // GET: Product
        public ActionResult Index()
        {
            var products = ProductRepository.GetAll();
            return View(products);
        }

        // Search
        public ActionResult Search(string val)
        {
            var result = ProductRepository.FindByName(val);
            return View("Index", result);
        }

        // GET: Product/Details/5
        public ActionResult Details(int id)
        {
            var product = ProductRepository.GetById(id);
            return View(product);
        }

        // GET: Product/Create
        public ActionResult Create()
        {
            // Populate the dropdown
            ViewBag.CategoryId = new SelectList(CategRepository.GetAll(), "CategoryId", "CategoryName");
            return View();
        }

        // POST: Product/Create
        [HttpPost]
        [ValidateAntiForgeryToken]
        public ActionResult Create(CreateViewModel model)
        {
            if (ModelState.IsValid)
            {
                string uniqueFileName = null;

                if (model.ImagePath != null)
                {
                    string uploadsFolder = Path.Combine(hostingEnvironment.WebRootPath, "images");
                    uniqueFileName = Guid.NewGuid().ToString() + "_" + model.ImagePath.FileName;
                    string filePath = Path.Combine(uploadsFolder, uniqueFileName);
                    model.ImagePath.CopyTo(new FileStream(filePath, FileMode.Create));
                }

                Product newProduct = new Product
                {
                    Name = model.Name,
                    Price = model.Price,
                    QteStock = model.QteStock,
                    CategoryId = model.CategoryId,
                    Image = uniqueFileName
                };

                ProductRepository.Add(newProduct);
                return RedirectToAction("Details", new { id = newProduct.ProductId });
            }
            ViewBag.CategoryId = new SelectList(CategRepository.GetAll(), "CategoryId", "CategoryName");
            return View(model);
        }

        // GET: Product/Edit/5
        public ActionResult Edit(int id)
        {
            var product = ProductRepository.GetById(id);
            if (product == null)
            {
                return NotFound();
            }

            EditViewModel editViewModel = new EditViewModel
            {
                ProductId = product.ProductId,
                Name = product.Name,
                Price = product.Price,
                QteStock = product.QteStock,
                CategoryId = product.CategoryId,
                ExistingPhotoPath = product.Image
            };

            ViewBag.CategoryId = new SelectList(CategRepository.GetAll(), "CategoryId", "CategoryName");
            return View(editViewModel);
        }

        // POST: Product/Edit/5
        [HttpPost]
        [ValidateAntiForgeryToken]
        public ActionResult Edit(EditViewModel model)
        {
            if (ModelState.IsValid)
            {
                Product existingProduct = ProductRepository.GetById(model.ProductId);

                if (existingProduct != null)
                {
                    existingProduct.Name = model.Name;
                    existingProduct.Price = model.Price;
                    existingProduct.QteStock = model.QteStock;
                    existingProduct.CategoryId = model.CategoryId;

                    // If a new photo is uploaded, replace the existing photo
                    if (model.ImagePath != null)
                    {
                        // Delete the old photo
                        if (!string.IsNullOrEmpty(existingProduct.Image))
                        {
                            string oldPhotoPath = Path.Combine(hostingEnvironment.WebRootPath, "images", existingProduct.Image);
                            if (System.IO.File.Exists(oldPhotoPath))
                            {
                                System.IO.File.Delete(oldPhotoPath);
                            }
                        }

                        // Save the new photo
                        string uniqueFileName = Guid.NewGuid().ToString() + "_" + model.ImagePath.FileName;
                        string uploadsFolder = Path.Combine(hostingEnvironment.WebRootPath, "images");
                        string filePath = Path.Combine(uploadsFolder, uniqueFileName);
                        model.ImagePath.CopyTo(new FileStream(filePath, FileMode.Create));

                        existingProduct.Image = uniqueFileName;
                    }

                    ProductRepository.Update(existingProduct);
                    return RedirectToAction("Details", new { id = existingProduct.ProductId });
                }
            }

            ViewBag.CategoryId = new SelectList(CategRepository.GetAll(), "CategoryId", "CategoryName");
            return View(model);
        }


        // GET: Product/Delete/5
        public ActionResult Delete(int id)
        {
            var product = ProductRepository.GetById(id);
            return View(product);
        }

        // POST: Product/Delete/5
        [HttpPost]
        [ValidateAntiForgeryToken]
        public ActionResult Delete(int id, Product product)
        {
            ProductRepository.Delete(id);
            return RedirectToAction(nameof(Index));
        }
    }
}